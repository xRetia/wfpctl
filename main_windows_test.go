//go:build windows

package main

import (
	"math"
	"testing"
	"unsafe"
)

func TestConstantsMatchWdk(t *testing.T) {
	cases := map[string]struct{ got, want uint32 }{
		"FWP_ACTION_BLOCK":                    {fwpActionBlock, 0x00001001},
		"FWP_ACTION_PERMIT":                   {fwpActionPermit, 0x00001002},
		"FWP_EMPTY":                           {fwpEmpty, 0},
		"FWP_UINT8":                           {fwpUint8, 1},
		"FWP_UINT16":                          {fwpUint16, 2},
		"FWP_UINT64":                          {fwpUint64, 4},
		"FWP_V4_ADDR_MASK":                    {fwpV4AddrMask, 0x100},
		"FWP_V6_ADDR_MASK":                    {fwpV6AddrMask, 0x101},
		"FWP_MATCH_EQUAL":                     {fwpMatchEqual, 0},
		"FWP_MATCH_GREATER_OR_EQUAL":          {fwpMatchGreaterOrEq, 3},
		"FWP_MATCH_LESS_OR_EQUAL":             {fwpMatchLessOrEq, 4},
		"FWPM_FILTER_FLAG_PERSISTENT":         {fwpmFilterPersistent, 0x00000001},
		"FWPM_FILTER_FLAG_CLEAR_ACTION_RIGHT": {fwpmFilterClearActionRight, 0x00000008},
	}
	for name, c := range cases {
		if c.got != c.want {
			t.Errorf("%s = 0x%x, want 0x%x", name, c.got, c.want)
		}
	}
}

func TestFWPMFilter0LayoutMatchesNative(t *testing.T) {
	if unsafe.Sizeof(action{}) != 20 {
		t.Fatalf("FWPM_ACTION0 size = %d, want 20", unsafe.Sizeof(action{}))
	}
	if unsafe.Offsetof(action{}.Type) != 0 {
		t.Errorf("action.Type offset = %d, want 0", unsafe.Offsetof(action{}.Type))
	}
	if unsafe.Offsetof(action{}.CalloutKey) != 4 {
		t.Errorf("action.CalloutKey offset = %d, want 4", unsafe.Offsetof(action{}.CalloutKey))
	}
	// The first ten members of FWPM_FILTER0 are the caller-supplied ones
	// (filterKey..action); their offsets must match the native layout.
	// Values differ between x64 (pointers = 8 bytes) and x86 (pointers = 4 bytes).
	var f filter
	var wantSize uintptr
	var off = map[string]uintptr{}
	if unsafe.Sizeof(uintptr(0)) == 8 {
		wantSize = 200
		off = map[string]uintptr{
			"FilterKey": 0, "Display": 16, "Flags": 32, "ProviderKey": 40,
			"ProviderData": 48, "LayerKey": 64, "SublayerKey": 80, "Weight": 96,
			"NumConditions": 112, "Conditions": 120, "Action": 128,
			"Action.Type": 0, "Action.CalloutKey": 4, "RawContext": 148,
			"Reserved": 168, "FilterID": 176, "EffectiveWeight": 184,
		}
	} else {
		// 32-bit (386): pointers are 4 bytes, uintptr align = 4.
		wantSize = 144
		off = map[string]uintptr{
			"FilterKey": 0, "Display": 16, "Flags": 24, "ProviderKey": 28,
			"ProviderData": 32, "LayerKey": 40, "SublayerKey": 56, "Weight": 72,
			"NumConditions": 80, "Conditions": 84, "Action": 88,
			"Action.Type": 0, "Action.CalloutKey": 4, "RawContext": 108,
			"Reserved": 124, "FilterID": 128, "EffectiveWeight": 136,
		}
	}
	checks := []struct {
		name string
		off  uintptr
	}{
		{"FilterKey", unsafe.Offsetof(f.FilterKey)},
		{"Display", unsafe.Offsetof(f.Display)},
		{"Flags", unsafe.Offsetof(f.Flags)},
		{"ProviderKey", unsafe.Offsetof(f.ProviderKey)},
		{"ProviderData", unsafe.Offsetof(f.ProviderData)},
		{"LayerKey", unsafe.Offsetof(f.LayerKey)},
		{"SublayerKey", unsafe.Offsetof(f.SublayerKey)},
		{"Weight", unsafe.Offsetof(f.Weight)},
		{"NumConditions", unsafe.Offsetof(f.NumConditions)},
		{"Conditions", unsafe.Offsetof(f.Conditions)},
		{"Action", unsafe.Offsetof(f.Action)},
		{"Action.Type", unsafe.Offsetof(f.Action.Type)},
		{"Action.CalloutKey", unsafe.Offsetof(f.Action.CalloutKey)},
		{"RawContext", unsafe.Offsetof(f.RawContext)},
		{"Reserved", unsafe.Offsetof(f.Reserved)},
		{"FilterID", unsafe.Offsetof(f.FilterID)},
		{"EffectiveWeight", unsafe.Offsetof(f.EffectiveWeight)},
	}
	for _, c := range checks {
		if c.off != off[c.name] {
			t.Errorf("offset(%s) = %d, want %d", c.name, c.off, off[c.name])
		}
	}
	if unsafe.Sizeof(f) != wantSize {
		t.Errorf("sizeof(FWPM_FILTER0) = %d, want %d (arch=x%d)",
			unsafe.Sizeof(f), wantSize, int(unsafe.Sizeof(uintptr(0)))*8)
	}
}

func TestParseTarget(t *testing.T) {
	cases := []struct {
		in      string
		bits    int
		isV4    bool
		wantErr bool
	}{
		{"1.2.3.4", 32, true, false},
		{"192.168.1.0/24", 24, true, false},
		{"10.0.0.1/8", 8, true, false},
		{"::ffff:1.2.3.4", 32, true, false},
		{"fe80::1", 128, false, false},
		{"2001:db8::/32", 32, false, false},
		{"not-an-ip", 0, false, true},
		{"", 0, false, true},
	}
	for _, c := range cases {
		p, err := parseTarget(c.in)
		if c.wantErr {
			if err == nil {
				t.Errorf("parseTarget(%q) = %v, want error", c.in, p)
			}
			continue
		}
		if err != nil {
			t.Errorf("parseTarget(%q): %v", c.in, err)
			continue
		}
		if p.Bits() != c.bits {
			t.Errorf("parseTarget(%q).Bits() = %d, want %d", c.in, p.Bits(), c.bits)
		}
		if p.Addr().Is4() != c.isV4 {
			t.Errorf("parseTarget(%q) Is4() = %v, want %v", c.in, p.Addr().Is4(), c.isV4)
		}
	}
	if p, _ := parseTarget("192.168.1.55/24"); p.Addr().String() != "192.168.1.0" {
		t.Errorf("192.168.1.55/24 masked to %q, want 192.168.1.0", p.Addr())
	}
}

func TestParsePortRange(t *testing.T) {
	cases := []struct {
		in      string
		lo, hi  uint16
		wantErr bool
	}{
		{"", 0, 0, false},
		{"80", 80, 80, false},
		{"80-443", 80, 443, false},
		{"65535", 65535, 65535, false},
		{"443-80", 0, 0, true},
		{"0", 0, 0, true},
		{"abc", 0, 0, true},
		{"80-", 0, 0, true},
	}
	for _, c := range cases {
		lo, hi, err := parsePortRange(c.in)
		if c.wantErr {
			if err == nil {
				t.Errorf("parsePortRange(%q) = %d-%d, want error", c.in, lo, hi)
			}
			continue
		}
		if err != nil {
			t.Errorf("parsePortRange(%q): %v", c.in, err)
			continue
		}
		if lo != c.lo || hi != c.hi {
			t.Errorf("parsePortRange(%q) = %d-%d, want %d-%d", c.in, lo, hi, c.lo, c.hi)
		}
	}
}

func TestRuleMetaRoundTrip(t *testing.T) {
	want := ruleMeta{Target: "192.168.1.0/24", Port: "80-443", Protocol: "tcp", Direction: "out", Action: "block", Priority: "highest", Weight: math.MaxUint64}
	pd, b, err := makeProviderData(want)
	if err != nil {
		t.Fatalf("makeProviderData: %v", err)
	}
	if pd.Size != uint32(len(b)) {
		t.Errorf("blob size = %d, want %d", pd.Size, len(b))
	}
	got := ruleMetaFrom(&filter{ProviderData: pd})
	if got != want {
		t.Errorf("round trip = %+v, want %+v", got, want)
	}
}

func TestRuleMetaFromEmptyOrBad(t *testing.T) {
	if got := ruleMetaFrom(&filter{}); got != (ruleMeta{}) {
		t.Errorf("empty blob = %+v, want zero", got)
	}
	bad := &filter{ProviderData: byteBlob{Size: 11, Data: &([]byte("not-json!..")[0])}}
	if got := ruleMetaFrom(bad); got != (ruleMeta{}) {
		t.Errorf("bad blob = %+v, want zero", got)
	}
}

func TestRuleLayersSelection(t *testing.T) {
	cases := []struct {
		name      string
		is4       bool
		direction string
		all       bool
		want      []string
	}{
		{"single out v4", true, "out", false, []string{"ALE_AUTH_CONNECT_V4"}},
		{"single out v6", false, "out", false, []string{"ALE_AUTH_CONNECT_V6"}},
		{"single in v4", true, "in", false, []string{"ALE_AUTH_RECV_ACCEPT_V4"}},
		{"single in v6", false, "in", false, []string{"ALE_AUTH_RECV_ACCEPT_V6"}},
		{"all out v4", true, "out", true, []string{"ALE_AUTH_CONNECT_V4", "ALE_CONNECT_REDIRECT_V4", "OUTBOUND_TRANSPORT_V4", "OUTBOUND_IPPACKET_V4", "STREAM_V4", "ALE_FLOW_ESTABLISHED_V4"}},
		{"all out v6", false, "out", true, []string{"ALE_AUTH_CONNECT_V6", "ALE_CONNECT_REDIRECT_V6", "OUTBOUND_TRANSPORT_V6", "OUTBOUND_IPPACKET_V6", "STREAM_V6", "ALE_FLOW_ESTABLISHED_V6"}},
		{"all in v4", true, "in", true, []string{"ALE_AUTH_RECV_ACCEPT_V4", "ALE_AUTH_RECV_ACCEPT_REDIRECT_V4", "INBOUND_TRANSPORT_V4", "INBOUND_IPPACKET_V4", "STREAM_V4", "ALE_FLOW_ESTABLISHED_V4"}},
		{"all in v6", false, "in", true, []string{"ALE_AUTH_RECV_ACCEPT_V6", "ALE_AUTH_RECV_ACCEPT_REDIRECT_V6", "INBOUND_TRANSPORT_V6", "INBOUND_IPPACKET_V6", "STREAM_V6", "ALE_FLOW_ESTABLISHED_V6"}},
	}
	for _, c := range cases {
		specs := ruleLayers(c.is4, c.direction, c.all)
		got := make([]string, len(specs))
		for i, s := range specs {
			got[i] = s.label
		}
		if len(got) != len(c.want) {
			t.Errorf("%s: got %d layers %v, want %d %v", c.name, len(got), got, len(c.want), c.want)
			continue
		}
		for i := range got {
			if got[i] != c.want[i] {
				t.Errorf("%s: layer[%d] = %s, want %s", c.name, i, got[i], c.want[i])
			}
		}
	}
}

func TestRuleLayersCapabilities(t *testing.T) {
	// The whole point of the capability table: every layer must support the
	// address condition (the rule is always target-address based), and only
	// layers that expose port/protocol fields may use those conditions.
	for _, c := range []bool{true, false} {
		for _, d := range []string{"out", "in"} {
			for _, all := range []bool{false, true} {
				for _, s := range ruleLayers(c, d, all) {
					if !s.addr {
						t.Errorf("%s: missing address condition support", s.label)
					}
				}
			}
		}
	}
}
