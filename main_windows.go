package main

import (
	"crypto/rand"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"math"
	"net/netip"
	"os"
	"sort"
	"strconv"
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

const (
	fwpEmpty                   = 0
	fwpUint8                   = 1
	fwpUint16                  = 2
	fwpUint64                  = 4
	fwpByteArray16             = 11
	fwpV4AddrMask              = 256
	fwpV6AddrMask              = 257
	fwpMatchEqual              = 0
	fwpMatchGreaterOrEq        = 3
	fwpMatchLessOrEq           = 4
	fwpActionBlock             = 0x00001001
	fwpActionPermit            = 0x00001002
	fwpmFilterPersistent       = 0x00000001
	fwpmFilterClearActionRight = 0x00000008
	fwpmSubLayerPersistent     = 0x00000001
	fwpmProviderPersistent     = 0x00000001
	authnServiceWinNT          = 10
)

type displayData struct{ Name, Description *uint16 }
type session struct {
	Key        windows.GUID
	Display    displayData
	Flags      uint32
	TxnWait    uint32
	ProcessID  uint32
	SID        *windows.SID
	Username   *uint16
	KernelMode uint8
}
type value struct {
	Type  uint32
	Value uintptr
}
type action struct {
	Type       uint32
	CalloutKey windows.GUID
}
type conditionValue struct {
	Type  uint32
	Value uintptr
}
type condition struct {
	FieldKey  windows.GUID
	MatchType uint32
	Value     conditionValue
}
type filter struct {
	FilterKey       windows.GUID
	Display         displayData
	Flags           uint32
	ProviderKey     *windows.GUID
	ProviderData    byteBlob
	LayerKey        windows.GUID
	SublayerKey     windows.GUID
	Weight          value
	NumConditions   uint32
	Conditions      *condition
	Action          action
	RawContext      [16]byte
	Reserved        *windows.GUID
	FilterID        uint64
	EffectiveWeight value
}
type byteBlob struct {
	Size uint32
	Data *uint8
}
type subLayer struct {
	SubLayerKey  windows.GUID
	Display      displayData
	Flags        uint32
	ProviderKey  *windows.GUID
	ProviderData byteBlob
	Weight       uint16
}
type provider struct {
	ProviderKey  windows.GUID
	Display      displayData
	Flags        uint32
	ProviderData byteBlob
	ServiceName  *uint16
}
type v4AddrMask struct{ Addr, Mask uint32 }
type v6AddrMask struct {
	Addr         [16]byte
	PrefixLength uint8
}

var (
	fwpuclnt            = windows.NewLazySystemDLL("fwpuclnt.dll")
	engineOpen          = fwpuclnt.NewProc("FwpmEngineOpen0")
	engineClose         = fwpuclnt.NewProc("FwpmEngineClose0")
	filterAdd           = fwpuclnt.NewProc("FwpmFilterAdd0")
	filterDelete        = fwpuclnt.NewProc("FwpmFilterDeleteByKey0")
	filterCreateEnum    = fwpuclnt.NewProc("FwpmFilterCreateEnumHandle0")
	filterEnum          = fwpuclnt.NewProc("FwpmFilterEnum0")
	filterDestroyEnum   = fwpuclnt.NewProc("FwpmFilterDestroyEnumHandle0")
	subLayerAdd         = fwpuclnt.NewProc("FwpmSubLayerAdd0")
	subLayerGet         = fwpuclnt.NewProc("FwpmSubLayerGetByKey0")
	subLayerDelete      = fwpuclnt.NewProc("FwpmSubLayerDeleteByKey0")
	subLayerCreateEnum  = fwpuclnt.NewProc("FwpmSubLayerCreateEnumHandle0")
	subLayerEnum        = fwpuclnt.NewProc("FwpmSubLayerEnum0")
	subLayerDestroyEnum = fwpuclnt.NewProc("FwpmSubLayerDestroyEnumHandle0")
	providerAdd         = fwpuclnt.NewProc("FwpmProviderAdd0")
	providerGet         = fwpuclnt.NewProc("FwpmProviderGetByKey0")
	providerDelete      = fwpuclnt.NewProc("FwpmProviderDeleteByKey0")
	freeMemory          = fwpuclnt.NewProc("FwpmFreeMemory0")
)

var (
	fieldRemoteAddress = windows.GUID{Data1: 0xb235ae9a, Data2: 0x1d64, Data3: 0x49b8, Data4: [8]byte{0xa4, 0x4c, 0x5f, 0xf3, 0xd9, 0x09, 0x50, 0x45}}
	fieldRemotePort    = windows.GUID{Data1: 0xc35a604d, Data2: 0xd22b, Data3: 0x4e1a, Data4: [8]byte{0x91, 0xb4, 0x68, 0xf6, 0x74, 0xee, 0x67, 0x4b}}
	fieldProtocol      = windows.GUID{Data1: 0x3971ef2b, Data2: 0x623e, Data3: 0x4f9a, Data4: [8]byte{0x8c, 0xb1, 0x6e, 0x79, 0xb8, 0x06, 0xb9, 0xa7}}
	layerConnect4      = windows.GUID{Data1: 0xc38d57d1, Data2: 0x05a7, Data3: 0x4c33, Data4: [8]byte{0x90, 0x4f, 0x7f, 0xbc, 0xee, 0xe6, 0x0e, 0x82}}
	layerConnect6      = windows.GUID{Data1: 0x4a72393b, Data2: 0x319f, Data3: 0x44bc, Data4: [8]byte{0x84, 0xc3, 0xba, 0x54, 0xdc, 0xb3, 0xb6, 0xb4}}
	layerRecv4         = windows.GUID{Data1: 0xe1cd9fe7, Data2: 0xf4b5, Data3: 0x4273, Data4: [8]byte{0x96, 0xc0, 0x59, 0x2e, 0x48, 0x7b, 0x86, 0x50}}
	layerRecv6         = windows.GUID{Data1: 0xa3b42c97, Data2: 0x9f04, Data3: 0x4672, Data4: [8]byte{0xb8, 0x7e, 0xce, 0xe9, 0xc4, 0x83, 0x25, 0x7f}}
	layerConnectRedir4 = windows.GUID{Data1: 0xc6e63c8c, Data2: 0xb784, Data3: 0x4562, Data4: [8]byte{0xaa, 0x7d, 0x0a, 0x67, 0xcf, 0xca, 0xf9, 0xa3}}
	layerConnectRedir6 = windows.GUID{Data1: 0x587e54a7, Data2: 0x8046, Data3: 0x42ba, Data4: [8]byte{0xa0, 0xaa, 0xb7, 0x16, 0x25, 0x0f, 0xc7, 0xfd}}
	layerRecvRedir4    = windows.GUID{Data1: 0x29243af8, Data2: 0xecaf, Data3: 0x4436, Data4: [8]byte{0xa4, 0x4e, 0xf9, 0xfb, 0x70, 0x70, 0xaa, 0x04}}
	layerRecvRedir6    = windows.GUID{Data1: 0xc9809347, Data2: 0x218f, Data3: 0x4b7f, Data4: [8]byte{0xa7, 0x42, 0xb2, 0x81, 0xa3, 0xf6, 0x31, 0xb4}}
	layerOutTran4      = windows.GUID{Data1: 0x09e61aea, Data2: 0xd214, Data3: 0x46e2, Data4: [8]byte{0x9b, 0x21, 0xb2, 0x6b, 0x0b, 0x2f, 0x28, 0xc8}}
	layerOutTran6      = windows.GUID{Data1: 0xe1735bde, Data2: 0x013f, Data3: 0x4655, Data4: [8]byte{0xb3, 0x51, 0xa4, 0x9e, 0x15, 0x76, 0x2d, 0xf0}}
	layerInTran4       = windows.GUID{Data1: 0x5926dfc8, Data2: 0xe3cf, Data3: 0x4426, Data4: [8]byte{0xa2, 0x83, 0xdc, 0x39, 0x3f, 0x5d, 0x0f, 0x9d}}
	layerInTran6       = windows.GUID{Data1: 0x634a869f, Data2: 0xfc23, Data3: 0x4b90, Data4: [8]byte{0xb0, 0xc1, 0xbf, 0x62, 0x0a, 0x36, 0xae, 0x6f}}
	layerOutIP4        = windows.GUID{Data1: 0x1e5c9fae, Data2: 0x8a84, Data3: 0x4135, Data4: [8]byte{0xa3, 0x31, 0x95, 0x0b, 0x54, 0x22, 0x9e, 0xcd}}
	layerOutIP6        = windows.GUID{Data1: 0x9513d7c4, Data2: 0xa934, Data3: 0x49dc, Data4: [8]byte{0x91, 0xa7, 0x6c, 0xcb, 0x80, 0xcc, 0x02, 0xe3}}
	layerInIP4         = windows.GUID{Data1: 0xb5a230d0, Data2: 0xa8c0, Data3: 0x44f2, Data4: [8]byte{0x91, 0x6e, 0x99, 0x1b, 0x53, 0xde, 0xd1, 0xf7}}
	layerInIP6         = windows.GUID{Data1: 0xf52032cb, Data2: 0x991c, Data3: 0x46e7, Data4: [8]byte{0x97, 0x1d, 0x26, 0x01, 0x45, 0x9a, 0x91, 0xca}}
	layerStream4       = windows.GUID{Data1: 0xaf52d8ec, Data2: 0xcb2d, Data3: 0x44e5, Data4: [8]byte{0xad, 0x92, 0xf8, 0xdc, 0x38, 0xd2, 0xeb, 0x29}}
	layerStream6       = windows.GUID{Data1: 0x779a8ca3, Data2: 0xf099, Data3: 0x468f, Data4: [8]byte{0xb5, 0xd4, 0x83, 0x53, 0x5c, 0x46, 0x1c, 0x02}}
	layerFlowEst4      = windows.GUID{Data1: 0xaf80470a, Data2: 0x5596, Data3: 0x4c13, Data4: [8]byte{0x99, 0x92, 0x53, 0x9e, 0x6f, 0xe5, 0x79, 0x67}}
	layerFlowEst6      = windows.GUID{Data1: 0x7021d2b3, Data2: 0xdfa4, Data3: 0x406e, Data4: [8]byte{0xaf, 0xeb, 0x6a, 0xfa, 0xf7, 0xe7, 0x0e, 0xfd}}
	providerKey        = windows.GUID{Data1: 0x502b4bcd, Data2: 0x7bf4, Data3: 0x4e46, Data4: [8]byte{0xb0, 0x06, 0x0c, 0x8b, 0xab, 0x4a, 0x27, 0x65}}
	subLayerKey        = windows.GUID{Data1: 0x5af52f9c, Data2: 0xee4d, Data3: 0x4a9f, Data4: [8]byte{0x85, 0x99, 0x94, 0xf0, 0xf5, 0x9e, 0x28, 0x9b}}
)

func call(proc *windows.LazyProc, args ...uintptr) error {
	r, _, e := proc.Call(args...)
	if r != 0 {
		return fmt.Errorf("%s: 0x%x (lastErr=%v)", proc.Name, r, e)
	}
	return nil
}
func utf16(s string) (*uint16, error) { p, e := windows.UTF16PtrFromString(s); return p, e }
func openEngine() (windows.Handle, error) {
	name, _ := utf16("wfpctl")
	s := session{Display: displayData{Name: name}, TxnWait: 15000}
	var h windows.Handle
	e := call(engineOpen, 0, authnServiceWinNT, 0, uintptr(unsafe.Pointer(&s)), uintptr(unsafe.Pointer(&h)))
	return h, e
}
func parseWeight(mode string, custom uint64) (uint64, error) {
	switch strings.ToLower(mode) {
	case "highest", "最高":
		return math.MaxUint64, nil
	case "lowest", "最低":
		return 1, nil
	case "custom", "自定义":
		return custom, nil
	default:
		return 0, fmt.Errorf("priority must be highest, lowest, or custom")
	}
}

func newGUID() (windows.GUID, error) {
	var g windows.GUID
	if _, err := rand.Read((*[16]byte)(unsafe.Pointer(&g))[:]); err != nil {
		return g, err
	}
	g.Data3 = (g.Data3 & 0x0fff) | 0x4000
	g.Data4[0] = (g.Data4[0] & 0x3f) | 0x80
	return g, nil
}

func ensureProvider(h windows.Handle) error {
	var p uintptr
	if e := call(providerGet, uintptr(h), uintptr(unsafe.Pointer(&providerKey)), uintptr(unsafe.Pointer(&p))); e != nil {
		name, _ := utf16("wfpctl Provider")
		prov := provider{ProviderKey: providerKey, Display: displayData{Name: name}, Flags: fwpmProviderPersistent}
		return call(providerAdd, uintptr(h), uintptr(unsafe.Pointer(&prov)), 0)
	}
	return nil
}

func enumSubLayerWeights(h windows.Handle) (map[uint16]string, error) {
	var enumHandle uintptr
	if err := call(subLayerCreateEnum, uintptr(h), 0, uintptr(unsafe.Pointer(&enumHandle))); err != nil {
		return nil, err
	}
	defer call(subLayerDestroyEnum, uintptr(h), enumHandle)
	weights := map[uint16]string{}
	sz := unsafe.Sizeof(uintptr(0))
	for {
		var count uint32
		var entries unsafe.Pointer
		if err := call(subLayerEnum, uintptr(h), enumHandle, 1000000, uintptr(unsafe.Pointer(&entries)), uintptr(unsafe.Pointer(&count))); err != nil {
			return nil, err
		}
		if count == 0 {
			call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
			break
		}
		for i := uint32(0); i < count; i++ {
			sl := (*subLayer)(*(*unsafe.Pointer)(unsafe.Add(entries, uintptr(i)*sz)))
			if _, ok := weights[sl.Weight]; !ok {
				weights[sl.Weight] = windows.UTF16PtrToString(sl.Display.Name)
			}
		}
		call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
	}
	return weights, nil
}

func pickSubLayerWeight(h windows.Handle) (uint16, string, error) {
	weights, err := enumSubLayerWeights(h)
	if err != nil {
		return 0, "", err
	}
	if _, occupied := weights[math.MaxUint16]; !occupied {
		return math.MaxUint16, "", nil
	}
	for w := uint16(math.MaxUint16 - 1); ; w-- {
		if _, occupied := weights[w]; !occupied {
			return w, weights[math.MaxUint16], nil
		}
		if w == 0 {
			return 0, weights[math.MaxUint16], errors.New("no free sublayer weight")
		}
	}
}

func ensureSubLayer(h windows.Handle) error {
	var p uintptr
	if e := call(subLayerGet, uintptr(h), uintptr(unsafe.Pointer(&subLayerKey)), uintptr(unsafe.Pointer(&p))); e != nil {
		w, holder, err := pickSubLayerWeight(h)
		if err != nil {
			return fmt.Errorf("pick sublayer weight: %w", err)
		}
		if w != math.MaxUint16 {
			fmt.Printf("subLayer: weight 65535 is held by %q, using highest free weight %d\n", holder, w)
		} else {
			fmt.Printf("subLayer: registered at weight %d (highest possible)\n", w)
		}
		name, _ := utf16("wfpctl SubLayer")
		sl := subLayer{SubLayerKey: subLayerKey, Display: displayData{Name: name}, Flags: fwpmSubLayerPersistent, ProviderKey: &providerKey, Weight: w}
		return call(subLayerAdd, uintptr(h), uintptr(unsafe.Pointer(&sl)), 0)
	}
	return nil
}

func layerLabel(g windows.GUID) string {
	switch g {
	case layerConnect4:
		return "ALE_AUTH_CONNECT_V4"
	case layerConnect6:
		return "ALE_AUTH_CONNECT_V6"
	case layerRecv4:
		return "ALE_AUTH_RECV_ACCEPT_V4"
	case layerRecv6:
		return "ALE_AUTH_RECV_ACCEPT_V6"
	case layerConnectRedir4:
		return "ALE_CONNECT_REDIRECT_V4"
	case layerConnectRedir6:
		return "ALE_CONNECT_REDIRECT_V6"
	case layerRecvRedir4:
		return "ALE_AUTH_RECV_ACCEPT_REDIRECT_V4"
	case layerRecvRedir6:
		return "ALE_AUTH_RECV_ACCEPT_REDIRECT_V6"
	case layerOutTran4:
		return "OUTBOUND_TRANSPORT_V4"
	case layerOutTran6:
		return "OUTBOUND_TRANSPORT_V6"
	case layerInTran4:
		return "INBOUND_TRANSPORT_V4"
	case layerInTran6:
		return "INBOUND_TRANSPORT_V6"
	case layerOutIP4:
		return "OUTBOUND_IPPACKET_V4"
	case layerOutIP6:
		return "OUTBOUND_IPPACKET_V6"
	case layerInIP4:
		return "INBOUND_IPPACKET_V4"
	case layerInIP6:
		return "INBOUND_IPPACKET_V6"
	case layerStream4:
		return "STREAM_V4"
	case layerStream6:
		return "STREAM_V6"
	case layerFlowEst4:
		return "ALE_FLOW_ESTABLISHED_V4"
	case layerFlowEst6:
		return "ALE_FLOW_ESTABLISHED_V6"
	}
	return g.String()
}
func directionLabel(g windows.GUID) string {
	switch g {
	case layerConnect4, layerConnect6, layerConnectRedir4, layerConnectRedir6, layerOutTran4, layerOutTran6, layerOutIP4, layerOutIP6:
		return "out"
	case layerRecv4, layerRecv6, layerRecvRedir4, layerRecvRedir6, layerInTran4, layerInTran6, layerInIP4, layerInIP6:
		return "in"
	case layerStream4, layerStream6, layerFlowEst4, layerFlowEst6:
		return "both"
	}
	return ""
}
func actionLabel(t uint32) string {
	switch t {
	case fwpActionBlock:
		return "block"
	case fwpActionPermit:
		return "allow"
	}
	return fmt.Sprintf("0x%x", t)
}
func weightLabel(f *filter) string {
	if f.Weight.Type == fwpUint64 {
		w := **(**uint64)(unsafe.Add(unsafe.Pointer(&f.Weight), unsafe.Offsetof(value{}.Value)))
		return strconv.FormatUint(w, 10)
	}
	if f.Weight.Type == fwpEmpty && f.Weight.Value == 0 {
		return "auto"
	}
	return fmt.Sprintf("0x%x:0x%x", f.Weight.Type, f.Weight.Value)
}
func resolveSubLayer(h windows.Handle, selector string) (windows.GUID, error) {
	if g, err := parseGUID(selector); err == nil {
		return g, nil
	}
	names, err := subLayerNames(h)
	if err != nil {
		return windows.GUID{}, err
	}
	for key, name := range names {
		if strings.EqualFold(name, selector) {
			return key, nil
		}
	}
	return windows.GUID{}, fmt.Errorf("sublayer %q not found (use GUID or exact name)", selector)
}

// matchFilter reports whether a filter belongs to wfpctl (only), all filters
// (showAll), or the given sublayer (subGUID, non-nil).
func matchFilter(f *filter, showAll bool, subGUID *windows.GUID) bool {
	if subGUID != nil {
		return f.SublayerKey == *subGUID
	}
	if showAll {
		return true
	}
	return f.ProviderKey != nil && *f.ProviderKey == providerKey
}

func listRules(showAll bool, subSelector string) error {
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	var subGUID *windows.GUID
	if subSelector != "" {
		g, err := resolveSubLayer(h, subSelector)
		if err != nil {
			return err
		}
		subGUID = &g
	}
	names, err := subLayerNames(h)
	if err != nil {
		return err
	}
	var enumHandle uintptr
	if err := call(filterCreateEnum, uintptr(h), 0, uintptr(unsafe.Pointer(&enumHandle))); err != nil {
		return fmt.Errorf("create filter enum: %w", err)
	}
	defer call(filterDestroyEnum, uintptr(h), enumHandle)
	sz := unsafe.Sizeof(uintptr(0))
	fmt.Printf("%-14s %-24s %-22s %-22s %-6s %6s %s\n", "FILTER ID", "NAME", "LAYER", "SUBLAYER", "ACTION", "WEIGHT", "GUID")
	for {
		var count uint32
		var entries unsafe.Pointer
		if err := call(filterEnum, uintptr(h), enumHandle, 1000000, uintptr(unsafe.Pointer(&entries)), uintptr(unsafe.Pointer(&count))); err != nil {
			return fmt.Errorf("enumerate filters: %w", err)
		}
		if count == 0 {
			call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
			break
		}
		for i := uint32(0); i < count; i++ {
			f := (*filter)(*(*unsafe.Pointer)(unsafe.Add(entries, uintptr(i)*sz)))
			if !matchFilter(f, showAll, subGUID) {
				continue
			}
			sn := "(default)"
			if n, ok := names[f.SublayerKey]; ok && n != "" {
				sn = n
			}
			fmt.Printf("%-14d %-24s %-22s %-22s %-6s %6s %s\n", f.FilterID, windows.UTF16PtrToString(f.Display.Name), layerLabel(f.LayerKey), sn, actionLabel(f.Action.Type), weightLabel(f), f.FilterKey.String())
		}
		call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
	}
	return nil
}

type ruleJSON struct {
	ID        uint64 `json:"id"`
	Name      string `json:"name"`
	Direction string `json:"direction"`
	Action    string `json:"action"`
	Layer     string `json:"layer"`
	Sublayer  string `json:"sublayer"`
	Weight    string `json:"weight"`
	Target    string `json:"target"`
	Port      string `json:"port"`
	Protocol  string `json:"protocol"`
	Key       string `json:"key"`
}

func listRulesJSON(showAll bool, subSelector string) error {
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	var subGUID *windows.GUID
	if subSelector != "" {
		g, err := resolveSubLayer(h, subSelector)
		if err != nil {
			return err
		}
		subGUID = &g
	}
	names, err := subLayerNames(h)
	if err != nil {
		return err
	}
	var enumHandle uintptr
	if err := call(filterCreateEnum, uintptr(h), 0, uintptr(unsafe.Pointer(&enumHandle))); err != nil {
		return fmt.Errorf("create filter enum: %w", err)
	}
	defer call(filterDestroyEnum, uintptr(h), enumHandle)
	sz := unsafe.Sizeof(uintptr(0))
	var rules []ruleJSON
	for {
		var count uint32
		var entries unsafe.Pointer
		if err := call(filterEnum, uintptr(h), enumHandle, 1000000, uintptr(unsafe.Pointer(&entries)), uintptr(unsafe.Pointer(&count))); err != nil {
			return fmt.Errorf("enumerate filters: %w", err)
		}
		if count == 0 {
			call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
			break
		}
		for i := uint32(0); i < count; i++ {
			f := (*filter)(*(*unsafe.Pointer)(unsafe.Add(entries, uintptr(i)*sz)))
			if !matchFilter(f, showAll, subGUID) {
				continue
			}
			meta := ruleMetaFrom(f)
			sn := "(default)"
			if n, ok := names[f.SublayerKey]; ok && n != "" {
				sn = n
			}
			rules = append(rules, ruleJSON{
				ID:        f.FilterID,
				Name:      windows.UTF16PtrToString(f.Display.Name),
				Direction: directionLabel(f.LayerKey),
				Action:    actionLabel(f.Action.Type),
				Layer:     layerLabel(f.LayerKey),
				Sublayer:  sn,
				Weight:    weightLabel(f),
				Target:    meta.Target,
				Port:      meta.Port,
				Protocol:  meta.Protocol,
				Key:       strings.Trim(f.FilterKey.String(), "{}"),
			})
		}
		call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(rules)
}

type subLayerInfo struct {
	Weight uint16
	Name   string
	Key    windows.GUID
}

func enumSubLayers(h windows.Handle) ([]subLayerInfo, error) {
	var enumHandle uintptr
	if err := call(subLayerCreateEnum, uintptr(h), 0, uintptr(unsafe.Pointer(&enumHandle))); err != nil {
		return nil, fmt.Errorf("create sublayer enum: %w", err)
	}
	defer call(subLayerDestroyEnum, uintptr(h), enumHandle)
	var all []subLayerInfo
	sz := unsafe.Sizeof(uintptr(0))
	for {
		var count uint32
		var entries unsafe.Pointer
		if err := call(subLayerEnum, uintptr(h), enumHandle, 1000000, uintptr(unsafe.Pointer(&entries)), uintptr(unsafe.Pointer(&count))); err != nil {
			return nil, fmt.Errorf("enumerate sublayers: %w", err)
		}
		if count == 0 {
			call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
			break
		}
		for i := uint32(0); i < count; i++ {
			sl := (*subLayer)(*(*unsafe.Pointer)(unsafe.Add(entries, uintptr(i)*sz)))
			all = append(all, subLayerInfo{sl.Weight, windows.UTF16PtrToString(sl.Display.Name), sl.SubLayerKey})
		}
		call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
	}
	return all, nil
}

func subLayerNames(h windows.Handle) (map[windows.GUID]string, error) {
	all, err := enumSubLayers(h)
	if err != nil {
		return nil, err
	}
	names := make(map[windows.GUID]string, len(all))
	for _, sl := range all {
		names[sl.Key] = sl.Name
	}
	return names, nil
}

func listSubLayers() error {
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	all, err := enumSubLayers(h)
	if err != nil {
		return err
	}
	sort.Slice(all, func(i, j int) bool { return all[i].Weight > all[j].Weight })
	fmt.Printf("%5s  %-24s  %s\n", "WEIGHT", "NAME", "GUID")
	for _, it := range all {
		mark := " "
		if it.Weight >= 32768 {
			mark = "*"
		}
		fmt.Printf("%5d  %-24s  %s %s\n", it.Weight, it.Name, strings.Trim(it.Key.String(), "{}"), mark)
	}
	return nil
}

func listSubLayersJSON() error {
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	all, err := enumSubLayers(h)
	if err != nil {
		return err
	}
	sort.Slice(all, func(i, j int) bool { return all[i].Weight > all[j].Weight })
	type itemJSON struct {
		Weight uint16 `json:"weight"`
		Name   string `json:"name"`
		Key    string `json:"key"`
	}
	out := make([]itemJSON, 0, len(all))
	for _, it := range all {
		out = append(out, itemJSON{it.Weight, it.Name, strings.Trim(it.Key.String(), "{}")})
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(out)
}

func enumFilterKeysBySublayer(h windows.Handle, sl windows.GUID) ([]windows.GUID, error) {
	var enumHandle uintptr
	if err := call(filterCreateEnum, uintptr(h), 0, uintptr(unsafe.Pointer(&enumHandle))); err != nil {
		return nil, fmt.Errorf("create filter enum: %w", err)
	}
	defer call(filterDestroyEnum, uintptr(h), enumHandle)
	sz := unsafe.Sizeof(uintptr(0))
	var keys []windows.GUID
	for {
		var count uint32
		var entries unsafe.Pointer
		if err := call(filterEnum, uintptr(h), enumHandle, 1000000, uintptr(unsafe.Pointer(&entries)), uintptr(unsafe.Pointer(&count))); err != nil {
			return nil, fmt.Errorf("enumerate filters: %w", err)
		}
		if count == 0 {
			call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
			break
		}
		for i := uint32(0); i < count; i++ {
			f := (*filter)(*(*unsafe.Pointer)(unsafe.Add(entries, uintptr(i)*sz)))
			if f.SublayerKey == sl {
				keys = append(keys, f.FilterKey)
			}
		}
		call(freeMemory, uintptr(unsafe.Pointer(&entries)), 0)
	}
	return keys, nil
}

func deleteSubLayerByKey(key string) error {
	g, err := parseGUID(key)
	if err != nil {
		return err
	}
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	var p uintptr
	if e := call(subLayerGet, uintptr(h), uintptr(unsafe.Pointer(&g)), uintptr(unsafe.Pointer(&p))); e != nil {
		return fmt.Errorf("subLayer %s not found", g.String())
	}
	keys, err := enumFilterKeysBySublayer(h, g)
	if err != nil {
		return err
	}
	for _, k := range keys {
		if err := call(filterDelete, uintptr(h), uintptr(unsafe.Pointer(&k))); err != nil {
			return fmt.Errorf("delete filter %s: %w", k.String(), err)
		}
		fmt.Printf("removed filter %s\n", k.String())
	}
	if err := call(subLayerDelete, uintptr(h), uintptr(unsafe.Pointer(&g))); err != nil {
		return fmt.Errorf("delete subLayer %s: %w (remove its filters first)", g.String(), err)
	}
	fmt.Printf("removed subLayer %s\n", g.String())
	return nil
}

func deleteOwnSubLayer() error {
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	deleted := 0
	keys, err := enumFilterKeysBySublayer(h, subLayerKey)
	if err != nil {
		return err
	}
	for _, k := range keys {
		if err := call(filterDelete, uintptr(h), uintptr(unsafe.Pointer(&k))); err != nil {
			return fmt.Errorf("delete filter %s: %w", k.String(), err)
		}
		fmt.Printf("removed filter %s\n", k.String())
		deleted++
	}
	var p uintptr
	if call(subLayerGet, uintptr(h), uintptr(unsafe.Pointer(&subLayerKey)), uintptr(unsafe.Pointer(&p))) == nil {
		if err := call(subLayerDelete, uintptr(h), uintptr(unsafe.Pointer(&subLayerKey))); err != nil {
			return err
		}
		fmt.Println("removed subLayer wfpctl SubLayer")
	}
	if call(providerGet, uintptr(h), uintptr(unsafe.Pointer(&providerKey)), uintptr(unsafe.Pointer(&p))) == nil {
		if err := call(providerDelete, uintptr(h), uintptr(unsafe.Pointer(&providerKey))); err != nil {
			return err
		}
		fmt.Println("removed provider wfpctl Provider")
	}
	if deleted == 0 {
		fmt.Println("no wfpctl filters in the sub-layer")
	}
	return nil
}

func parseTarget(t string) (netip.Prefix, error) {
	if !strings.Contains(t, "/") {
		a, err := netip.ParseAddr(t)
		if err != nil {
			return netip.Prefix{}, fmt.Errorf("invalid target: %w", err)
		}
		a = a.Unmap()
		return netip.PrefixFrom(a, a.BitLen()), nil
	}
	p, err := netip.ParsePrefix(t)
	if err != nil {
		return netip.Prefix{}, fmt.Errorf("invalid CIDR: %w", err)
	}
	return p.Masked(), nil
}

func parsePortRange(s string) (uint16, uint16, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, 0, nil
	}
	parse := func(v string) (uint16, error) {
		n, e := strconv.ParseUint(v, 10, 16)
		if e != nil {
			return 0, fmt.Errorf("invalid port %q", v)
		}
		if n == 0 {
			return 0, fmt.Errorf("port must be 1-65535")
		}
		return uint16(n), nil
	}
	if lo, hiStr, ok := strings.Cut(s, "-"); ok {
		l, e := parse(lo)
		if e != nil {
			return 0, 0, e
		}
		h, e := parse(hiStr)
		if e != nil {
			return 0, 0, e
		}
		if l > h {
			return 0, 0, fmt.Errorf("port range start %d > end %d", l, h)
		}
		return l, h, nil
	}
	v, e := parse(s)
	if e != nil {
		return 0, 0, e
	}
	return v, v, nil
}

type ruleMeta struct {
	Target    string `json:"target"`
	Port      string `json:"port"`
	Protocol  string `json:"protocol"`
	Direction string `json:"direction"`
	Action    string `json:"action"`
	Priority  string `json:"priority"`
	Weight    uint64 `json:"weight"`
}

func makeProviderData(m ruleMeta) (byteBlob, []byte, error) {
	b, err := json.Marshal(m)
	if err != nil {
		return byteBlob{}, nil, err
	}
	return byteBlob{Size: uint32(len(b)), Data: &b[0]}, b, nil
}

func ruleMetaFrom(f *filter) ruleMeta {
	if f.ProviderData.Data == nil || f.ProviderData.Size == 0 {
		return ruleMeta{}
	}
	b := unsafe.Slice(f.ProviderData.Data, int(f.ProviderData.Size))
	var m ruleMeta
	if err := json.Unmarshal(b, &m); err != nil {
		return ruleMeta{}
	}
	return m
}

// layerSpec describes one placement layer for a rule and which of the three
// conditions it supports.  Layers that lack a field in FWPM_LAYER0 (verified
// by probing) drop the unsupported condition instead of failing with
// FWP_E_CONDITION_NOT_FOUND (0x80320002).
type layerSpec struct {
	key   windows.GUID
	label string
	addr  bool
	port  bool
	proto bool
}

func ruleLayers(is4 bool, direction string, all bool) []layerSpec {
	out := []layerSpec{
		{layerConnect4, "ALE_AUTH_CONNECT_V4", true, true, true},
		{layerConnectRedir4, "ALE_CONNECT_REDIRECT_V4", true, true, true},
		{layerOutTran4, "OUTBOUND_TRANSPORT_V4", true, true, true},
		{layerOutIP4, "OUTBOUND_IPPACKET_V4", true, false, false},
		{layerStream4, "STREAM_V4", true, true, false},
		{layerFlowEst4, "ALE_FLOW_ESTABLISHED_V4", true, true, true},
	}
	in := []layerSpec{
		{layerRecv4, "ALE_AUTH_RECV_ACCEPT_V4", true, true, true},
		{layerRecvRedir4, "ALE_AUTH_RECV_ACCEPT_REDIRECT_V4", true, true, true},
		{layerInTran4, "INBOUND_TRANSPORT_V4", true, true, true},
		{layerInIP4, "INBOUND_IPPACKET_V4", true, false, false},
		{layerStream4, "STREAM_V4", true, true, false},
		{layerFlowEst4, "ALE_FLOW_ESTABLISHED_V4", true, true, true},
	}
	if !is4 {
		out = []layerSpec{
			{layerConnect6, "ALE_AUTH_CONNECT_V6", true, true, true},
			{layerConnectRedir6, "ALE_CONNECT_REDIRECT_V6", true, true, true},
			{layerOutTran6, "OUTBOUND_TRANSPORT_V6", true, true, true},
			{layerOutIP6, "OUTBOUND_IPPACKET_V6", true, false, false},
			{layerStream6, "STREAM_V6", true, true, false},
			{layerFlowEst6, "ALE_FLOW_ESTABLISHED_V6", true, true, true},
		}
		in = []layerSpec{
			{layerRecv6, "ALE_AUTH_RECV_ACCEPT_V6", true, true, true},
			{layerRecvRedir6, "ALE_AUTH_RECV_ACCEPT_REDIRECT_V6", true, true, true},
			{layerInTran6, "INBOUND_TRANSPORT_V6", true, true, true},
			{layerInIP6, "INBOUND_IPPACKET_V6", true, false, false},
			{layerStream6, "STREAM_V6", true, true, false},
			{layerFlowEst6, "ALE_FLOW_ESTABLISHED_V6", true, true, true},
		}
	}
	if !all {
		if direction == "in" {
			return in[:1]
		}
		return out[:1]
	}
	if direction == "in" {
		return in
	}
	return out
}

func addRule(name, target, direction, actionName, protocol, portStr, priority, subLayerMode string, custom uint64, allLayers bool) error {
	prefix, err := parseTarget(target)
	if err != nil {
		return err
	}
	weight, err := parseWeight(priority, custom)
	if err != nil {
		return err
	}
	is4 := prefix.Addr().Is4()
	name16, _ := utf16(name)
	desc16, _ := utf16("created by wfpctl")
	subnet := prefix.Masked()

	// Build the address condition once; port and protocol conditions are
	// built per placement layer because not every layer exposes those fields
	// (e.g. IPPACKET layers have no port/protocol, STREAM layers have no
	// protocol).  Value pointers stay alive for the whole function via keep.
	var keep []any
	var addrs []condition
	if is4 {
		b := subnet.Addr().As4()
		var mask uint32
		for i := 0; i < subnet.Bits(); i++ {
			mask |= 1 << (31 - uint(i))
		}
		v4 := &v4AddrMask{Addr: uint32(b[0])<<24 | uint32(b[1])<<16 | uint32(b[2])<<8 | uint32(b[3]), Mask: mask}
		keep = append(keep, v4)
		addrs = []condition{{FieldKey: fieldRemoteAddress, MatchType: fwpMatchEqual, Value: conditionValue{Type: fwpV4AddrMask, Value: uintptr(unsafe.Pointer(v4))}}}
	} else {
		v6 := &v6AddrMask{Addr: subnet.Addr().As16(), PrefixLength: uint8(subnet.Bits())}
		keep = append(keep, v6)
		addrs = []condition{{FieldKey: fieldRemoteAddress, MatchType: fwpMatchEqual, Value: conditionValue{Type: fwpV6AddrMask, Value: uintptr(unsafe.Pointer(v6))}}}
	}
	portLo, portHi, err := parsePortRange(portStr)
	if err != nil {
		return err
	}
	meta := ruleMeta{Target: target, Port: portStr, Protocol: strings.ToLower(protocol), Direction: direction, Action: actionName, Priority: priority, Weight: weight}
	pd, pdBytes, err := makeProviderData(meta)
	if err != nil {
		return fmt.Errorf("encode metadata: %w", err)
	}
	keep = append(keep, pdBytes)
	h, err := openEngine()
	if err != nil {
		return fmt.Errorf("open WFP engine (run as Administrator): %w", err)
	}
	defer call(engineClose, uintptr(h))
	if err := ensureProvider(h); err != nil {
		return fmt.Errorf("ensure provider: %w", err)
	}
	s := windows.GUID{}
	if subLayerMode != "default" {
		if err := ensureSubLayer(h); err != nil {
			return fmt.Errorf("ensure sublayer: %w", err)
		}
		s = subLayerKey
	}
	for _, spec := range ruleLayers(is4, direction, allLayers) {
		conds := append([]condition(nil), addrs...)
		if spec.port && portLo != 0 {
			lo16, hi16 := uint16(portLo), uint16(portHi)
			if portLo == portHi {
				keep = append(keep, &lo16)
				conds = append(conds, condition{FieldKey: fieldRemotePort, MatchType: fwpMatchEqual, Value: conditionValue{Type: fwpUint16, Value: uintptr(unsafe.Pointer(&lo16))}})
			} else {
				keep = append(keep, &lo16, &hi16)
				conds = append(conds,
					condition{FieldKey: fieldRemotePort, MatchType: fwpMatchGreaterOrEq, Value: conditionValue{Type: fwpUint16, Value: uintptr(unsafe.Pointer(&lo16))}},
					condition{FieldKey: fieldRemotePort, MatchType: fwpMatchLessOrEq, Value: conditionValue{Type: fwpUint16, Value: uintptr(unsafe.Pointer(&hi16))}},
				)
			}
		}
		if spec.proto && protocol != "" {
			n, e := strconv.ParseUint(protocol, 10, 8)
			if e != nil {
				switch strings.ToLower(protocol) {
				case "tcp":
					n = 6
				case "udp":
					n = 17
				default:
					return fmt.Errorf("protocol must be tcp, udp, or a number")
				}
			}
			pv := uint8(n)
			keep = append(keep, &pv)
			conds = append(conds, condition{FieldKey: fieldProtocol, MatchType: fwpMatchEqual, Value: conditionValue{Type: fwpUint8, Value: uintptr(unsafe.Pointer(&pv))}})
		}
		key, err := newGUID()
		if err != nil {
			return fmt.Errorf("generate filter key: %w", err)
		}
		f := filter{FilterKey: key, Display: displayData{Name: name16, Description: desc16}, Flags: fwpmFilterPersistent, ProviderKey: &providerKey, ProviderData: pd, LayerKey: spec.key, SublayerKey: s, Weight: value{Type: fwpUint64, Value: uintptr(unsafe.Pointer(&weight))}, NumConditions: uint32(len(conds)), Conditions: &conds[0]}
		if actionName == "allow" {
			f.Action.Type = fwpActionPermit
			f.Flags |= fwpmFilterClearActionRight
		} else {
			f.Action.Type = fwpActionBlock
		}
		var id uint64
		err = call(filterAdd, uintptr(h), uintptr(unsafe.Pointer(&f)), 0, uintptr(unsafe.Pointer(&id)))
		if err != nil {
			return fmt.Errorf("add WFP filter to %s: %w", spec.label, err)
		}
		if allLayers {
			fmt.Printf("filter added: layer=%-26s key=%s id=%d weight=%d\n", spec.label, f.FilterKey.String(), id, weight)
		} else {
			fmt.Printf("filter added: key=%s id=%d weight=%d\n", f.FilterKey.String(), id, weight)
		}
	}
	return nil
}
func parseGUID(s string) (windows.GUID, error) {
	var g windows.GUID
	s = strings.TrimSpace(s)
	s = strings.TrimPrefix(s, "{")
	s = strings.TrimSuffix(s, "}")
	parts := strings.Split(s, "-")
	if len(parts) != 5 {
		return g, errors.New("GUID must be 8-4-4-4-12 hex")
	}
	hex8 := func(h string, bits int) (uint64, error) {
		if len(h)*4 != bits {
			return 0, errors.New("bad hex length")
		}
		return strconv.ParseUint(h, 16, bits)
	}
	d1, e := hex8(parts[0], 32)
	if e != nil {
		return g, e
	}
	d2, e := hex8(parts[1], 16)
	if e != nil {
		return g, e
	}
	d3, e := hex8(parts[2], 16)
	if e != nil {
		return g, e
	}
	tail := parts[3] + parts[4]
	if len(tail) != 16 {
		return g, errors.New("bad tail length")
	}
	for i := 0; i < 16; i += 2 {
		b, e := strconv.ParseUint(tail[i:i+2], 16, 8)
		if e != nil {
			return g, e
		}
		g.Data4[i/2] = byte(b)
	}
	g.Data1, g.Data2, g.Data3 = uint32(d1), uint16(d2), uint16(d3)
	return g, nil
}

func deleteRule(key string) error {
	g, err := parseGUID(key)
	if err != nil {
		return err
	}
	h, err := openEngine()
	if err != nil {
		return err
	}
	defer call(engineClose, uintptr(h))
	return call(filterDelete, uintptr(h), uintptr(unsafe.Pointer(&g)))
}

var (
	versionStr = "1.0.0"
	copyright  = "Copyright (c) 2026 xRetia Labs"
	repoURL    = "https://github.com/xRetia/wfpctl"
)

func printBanner() {
	fmt.Fprintln(os.Stderr, copyright)
	fmt.Fprintln(os.Stderr, repoURL)
}

func fsUsage(cmd, desc string, fs *flag.FlagSet) {
	fs.Usage = func() {
		fmt.Fprintf(os.Stderr, "usage: wfpctl %s %s\n\n", cmd, desc)
		fs.PrintDefaults()
		fmt.Fprintln(os.Stderr)
		printBanner()
	}
}

func printVersion() {
	fmt.Printf("wfpctl %s\n", versionStr)
	fmt.Println(copyright)
	fmt.Println(repoURL)
}

func mainUsage(exit func(int)) {
	fmt.Fprintln(os.Stderr, "usage: wfpctl <command> [flags]")
	fmt.Fprintln(os.Stderr, "commands: add, delete, list, sublayers, version, help")
	fmt.Fprintln(os.Stderr)
	printBanner()
	if exit != nil {
		exit(2)
	}
}

func main() {
	if len(os.Args) < 2 {
		mainUsage(os.Exit)
	}
	switch os.Args[1] {
	case "help", "-h", "--help":
		mainUsage(nil)
	case "version", "--version":
		printVersion()
	case "add":
		fs := flag.NewFlagSet("add", flag.ExitOnError)
		fsUsage("add", "[flags]", fs)
		name := fs.String("name", "wfpctl-rule", "rule name")
		target := fs.String("target", "", "remote IP or CIDR (e.g. 192.168.1.0/24)")
		direction := fs.String("direction", "out", "in or out")
		act := fs.String("action", "block", "block or allow")
		proto := fs.String("protocol", "", "tcp, udp, or number")
		port := fs.String("port", "", "remote port or range (e.g. 80 or 80-443)")
		pri := fs.String("priority", "highest", "highest, lowest, or custom")
		custom := fs.Uint64("weight", 0, "custom uint64 weight")
		sub := fs.String("sublayer", "high", "high (own highest-free sublayer) or default")
		allLayers := fs.Bool("all-layers", false, "add rule to every relevant WFP layer (redirect, transport, IP packet, stream, flow) for this direction")
		_ = fs.Parse(os.Args[2:])
		if *target == "" {
			fs.Usage()
			os.Exit(2)
		}
		if *direction != "in" && *direction != "out" {
			panic(errors.New("direction must be in or out"))
		}
		if *act != "block" && *act != "allow" {
			panic(errors.New("action must be block or allow"))
		}
		if *sub != "high" && *sub != "default" {
			panic(errors.New("sublayer must be high or default"))
		}
		if err := addRule(*name, *target, *direction, *act, *proto, *port, *pri, *sub, *custom, *allLayers); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	case "delete":
		var key string
		for i, a := range os.Args[2:] {
			if a == "-h" || a == "--help" {
				mainUsage(nil)
				return
			}
			if a == "-key" && i+1 < len(os.Args[2:]) {
				key = os.Args[2:][i+1]
				break
			}
		}
		if key == "" {
			fmt.Fprintln(os.Stderr, "usage: wfpctl delete -key <GUID>")
			os.Exit(2)
		}
		if err := deleteRule(key); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	case "list":
		jsonOut := false
		showAll := false
		subSelector := ""
		args := os.Args[2:]
		for i := 0; i < len(args); i++ {
			a := args[i]
			if a == "-h" || a == "--help" {
				mainUsage(nil)
				return
			}
			if a == "-json" {
				jsonOut = true
			}
			if a == "-all" {
				showAll = true
			}
			if a == "-sublayer" && i+1 < len(args) {
				subSelector = args[i+1]
				i++
			}
		}
		if jsonOut {
			if err := listRulesJSON(showAll, subSelector); err != nil {
				fmt.Fprintln(os.Stderr, err)
				os.Exit(1)
			}
		} else {
			if err := listRules(showAll, subSelector); err != nil {
				fmt.Fprintln(os.Stderr, err)
				os.Exit(1)
			}
		}
	case "sublayers":
		fs := flag.NewFlagSet("sublayers", flag.ExitOnError)
		fsUsage("sublayers", "[flags]", fs)
		del := fs.Bool("delete", false, "delete a sub-layer")
		key := fs.String("key", "", "sub-layer GUID to delete (omit to delete wfpctl's own)")
		jsonOut := fs.Bool("json", false, "output sub-layers as JSON")
		_ = fs.Parse(os.Args[2:])
		var err error
		switch {
		case *del && *key != "":
			err = deleteSubLayerByKey(*key)
		case *del:
			err = deleteOwnSubLayer()
		case *jsonOut:
			err = listSubLayersJSON()
		case *key != "":
			err = errors.New("-key requires -delete")
		default:
			err = listSubLayers()
		}
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	default:
		fmt.Fprintln(os.Stderr, "unknown command")
		mainUsage(nil)
		os.Exit(2)
	}
}
