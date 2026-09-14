//go:build windows

package main

import (
	"testing"
	"unsafe"
)

func TestConstantsMatchWdk(t *testing.T) {
	cases := map[string]struct{ got, want uint32 }{
		"FWP_ACTION_BLOCK":  {fwpActionBlock, 0x00001001},
		"FWP_ACTION_PERMIT": {fwpActionPermit, 0x00001002},
		"FWP_EMPTY":         {fwpEmpty, 0},
		"FWP_UINT8":         {fwpUint8, 1},
		"FWP_UINT16":        {fwpUint16, 2},
		"FWP_UINT64":        {fwpUint64, 4},
		"FWP_V4_ADDR_MASK":  {fwpV4AddrMask, 0x100},
		"FWP_V6_ADDR_MASK":  {fwpV6AddrMask, 0x101},
		"FWP_MATCH_EQUAL":   {fwpMatchEqual, 0},
		"FWP_MATCH_GREATER_OR_EQUAL": {fwpMatchGreaterOrEq, 3},
		"FWP_MATCH_LESS_OR_EQUAL":    {fwpMatchLessOrEq, 4},
		"FWPM_FILTER_FLAG_PERSISTENT":           {fwpmFilterPersistent, 0x00000001},
		"FWPM_FILTER_FLAG_CLEAR_ACTION_RIGHT":   {fwpmFilterClearActionRight, 0x00000008},
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