"""Emit src/psx_drop_missing_table.h from the agreed assignment.

Two things get baked:
  * the placements themselves (card, band, weight, duelist)
  * a fingerprint per duelist, so the mod can tell WHO the resident drop table
    belongs to without a duelist-id variable we have not reverse engineered.

The fingerprint covers the duelist's deck pool plus its three drop tiers -- the
four 1444-byte weight arrays the game leaves resident at 0x801781D8, stride
1460. Drops alone collide on three pairs (Heishin/Heishin 2nd share a table);
deck+drops is unique for all 39, the only clash being the unused record 0
against Simon Muran, which cannot arise because record 0 is never loaded.
"""
import json, os, struct

SCR = r'C:\Users\Unchiga\AppData\Local\Temp\claude\C--dev\18e747b9-4f54-416d-945c-3a6345879a26\scratchpad'
OUT = r'C:\dev\memories\YuGiOhForbiddenMemoriesRecomp\src\psx_drop_missing_table.h'
buf = open(os.path.join(SCR, 'WA_MRG_MRG.bin'), 'rb').read()
DROP0, REC, TIER = 15310260, 6144, 1460
roster = [l for l in open(os.path.join(SCR, 'duelists.txt')).read().split('\n') if l][:39]
rows = json.load(open(os.path.join(SCR, 'final_assignment.json')))

def fnv(data):
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h

def fingerprint(rec):
    """deck + tier0..2, 1444 bytes each, exactly as they sit in RAM."""
    d = b''
    for k in range(4):
        o = DROP0 + rec * REC + (k - 1) * TIER
        d += buf[o:o + 1444]
    return fnv(d)

fps = [fingerprint(r + 1) for r in range(39)]
assert len(set(fps)) == 39, 'fingerprints are not unique'

by_duelist = {}
for x in rows:
    by_duelist.setdefault(x['duelist_index'], []).append(x)

L = []
L.append('/* psx_drop_missing_table.h -- GENERATED, do not hand-edit.')
L.append(' *')
L.append(' * Default placements for MODS > DROP MISSING CARDS, plus one fingerprint per')
L.append(' * duelist so the running game can be identified from its resident drop data.')
L.append(' * Regenerate with tools/gen_drop_table.py.')
L.append(' */')
L.append('#ifndef PSX_DROP_MISSING_TABLE_H')
L.append('#define PSX_DROP_MISSING_TABLE_H')
L.append('')
L.append('#include <stdint.h>')
L.append('')
L.append('typedef struct { uint16_t card; uint8_t tier; uint16_t weight; } PsxDropAdd;')
L.append('typedef struct {')
L.append('    const char       *name;')
L.append('    uint32_t          fingerprint;   /* FNV-1a over deck + 3 drop tiers */')
L.append('    const PsxDropAdd *adds;')
L.append('    uint8_t           n_adds;')
L.append('} PsxDropDuelist;')
L.append('')
TN = {0: 'S/A POW', 1: 'B/C/D', 2: 'S/A TEC'}
for r in range(39):
    items = sorted(by_duelist.get(r, []), key=lambda x: (x['tier'], -x['weight']))
    if not items:
        continue
    L.append('static const PsxDropAdd PSX_DROP_D%02d[] = {   /* %s */' % (r, roster[r]))
    for x in items:
        L.append('    { %3d, %d, %3d },   /* %-9s %-30s */' %
                 (x['id'], x['tier'], x['weight'], TN[x['tier']], x['name']))
    L.append('};')
L.append('')
names = {}
for x in rows: names[x['id']] = x['name']
L.append('typedef struct { uint16_t card; const char *name; } PsxDropName;')
L.append('static const PsxDropName PSX_DROP_NAMES[] = {')
for c in sorted(names):
    L.append('    { %3d, "%s" },' % (c, names[c].replace('"', "'")))
L.append('};')
L.append('#define PSX_DROP_NAME_COUNT %d' % len(names))
L.append('')
L.append('static const PsxDropDuelist PSX_DROP_DUELISTS[39] = {')
for r in range(39):
    items = by_duelist.get(r, [])
    if items:
        L.append('    { "%s", 0x%08Xu, PSX_DROP_D%02d, %d },' % (roster[r], fps[r], r, len(items)))
    else:
        L.append('    { "%s", 0x%08Xu, 0, 0 },' % (roster[r], fps[r]))
L.append('};')
L.append('')
L.append('/* The four weight arrays the game leaves resident for the current opponent:')
L.append(' * deck pool first, then drop tiers 0..2, 722 u16 each, stride 1460 bytes. */')
L.append('#define PSX_DROP_RESIDENT_BASE  0x801781D8u')
L.append('#define PSX_DROP_TABLE_STRIDE   1460u')
L.append('#define PSX_DROP_CARDS          722u')
L.append('#define PSX_DROP_TIER_TOTAL     2048u')
L.append('')
L.append('#endif /* PSX_DROP_MISSING_TABLE_H */')
open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('wrote %s' % OUT)
print('duelists with adds: %d, placements: %d' % (len(by_duelist), len(rows)))
print('fingerprints unique: %s' % (len(set(fps)) == 39))
