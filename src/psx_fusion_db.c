/* psx_fusion_db.c — the game's fusion data, read live. See psx_fusion_db.h.
 *
 * ---- how a fusion is decided ----------------------------------------------
 *
 * Forbidden Memories resolves a two-card summon in func_8001A280, which makes
 * exactly three attempts and takes the first that answers (established by
 * tracing the calls during a real in-duel fusion, 2026-08-18):
 *
 *     v0 = func_80019A60(first, second)          the fusion table
 *     if (v0) -> that card is summoned
 *     v0 = func_80019A08(second, first)          equip table, one order
 *     if (v0) -> v0 (== first) survives
 *     v0 = func_80019A08(first, second)          equip table, other order
 *     if (v0) -> v0 (== second) survives
 *     otherwise no fusion: `second` is summoned as itself
 *
 * The two ids it passes come from the 28-byte card records the duel keeps at
 * 0x801A7AE4 (`lh a0, 14016(v0)` with v0 = slot*28 + 0x801A4424); the id is at
 * record+0. psx_fusion_assist.c owns that array.
 *
 * ---- func_80019A60: the fusion table --------------------------------------
 *
 * Base 0x8017C2D8. The routine sorts its arguments first, so a pair is stored
 * exactly once, under min(a,b), with max(a,b) as the partner:
 *
 *     off = u16 at base + min*2          0 -> this card fuses with nothing
 *     rec = base + off
 *     count = rec[0]                     body at rec+1
 *             ...unless rec[0] == 0, in which case
 *             count = 511 - rec[1]       body at rec+2   (counts 256..511)
 *
 * The body is groups of FIVE bytes, each carrying TWO (partner, result) pairs.
 * Card ids are 10 bits, and the four high halves are packed into the group's
 * first byte, two bits each:
 *
 *     partner1 = ((g[0] << 8) & 0x300) | g[1]
 *     result1  = ((g[0] << 6) & 0x300) | g[2]
 *     partner2 = ((g[0] << 4) & 0x300) | g[3]
 *     result2  = ((g[0] << 2) & 0x300) | g[4]
 *
 * The guest's loop consumes two entries per group and stops on `count <= 0`
 * AFTER the decrement, so an odd count still tests both halves of the final
 * group. That trailing half is padding — every one of them decodes to a result
 * of 0, which the caller reads as "no fusion" anyway — so scanning it, as the
 * loop below does, matches the game without needing to special-case it.
 *
 * ---- func_80019A08: the equip table ---------------------------------------
 *
 * Base 0x8017A1D8. A flat list of groups, terminated by a zero key:
 *
 *     u16 key            an equip card
 *     u16 count
 *     u16 member[count]  the monsters it may attach to
 *
 * The routine returns its SECOND argument when that argument is in the first
 * argument's member list. That is the equip mechanic: the monster stays on the
 * field and the equip powers it up, so the monster is the "result". 34 groups
 * covering 4041 memberships in the shipping data — this is the whole of the
 * "magic cards that fuse" behaviour.
 *
 * ---- why read the tables instead of calling the guest ---------------------
 *
 * psx_card_drops.c re-runs the game's own drop roll through psx_dispatch_call
 * because that roll is stateful: it draws from a per-opponent pool and burns
 * RNG, and reimplementing it would silently drift. Nothing here is stateful.
 * These are two static tables in the game's data segment, and the lookups are
 * the pure functions transcribed above, so reading the tables IS the game's
 * answer — with none of the cost or risk of re-entering guest code from a
 * frame tick, which is what an assistant that re-evaluates on every hand
 * change would be doing dozens of times a second.
 *
 * Both tables are DUEL data: the game streams them in from disc when a duel
 * starts and they read back as solid zeros everywhere else, the same way the
 * rank coefficients psx_rank_logic.c uses do. That is why readiness is probed
 * rather than assumed, and why this module answers only inside a duel -- which
 * is the only place the question is asked anyway.
 *
 * Checked against the game itself rather than against a FAQ: five pairs were
 * injected into a live duel's hand records and summoned, and the game produced
 * exactly what these tables predict, including two cases where the widely
 * mirrored GameFAQs fusion list is wrong (Air Marmot of Nefariousness +
 * Greenkappa is Tiger Axe, not Flower Wolf; Dissolverock + Skull Servant is
 * Stone Ghost, not Flame Ghost) and one where it invents a fusion that does
 * not exist (Bone Mouse + Skull Servant).
 */

#include "psx_fusion_db.h"

#include "mod_plugins.h"

#define PSX_FUSION_PAIR_BASE   0x8017C2D8u
#define PSX_FUSION_EQUIP_BASE  0x8017A1D8u
/* The index array is one u16 per card id plus entry 0, so the first record
 * cannot start before it ends. Doubles as the validation floor. */
#define PSX_FUSION_INDEX_BYTES ((PSX_FUSION_CARD_ID_MAX + 1) * 2)
/* Generous walk limits. The shipping tables are 34 equip groups and 578 cards
 * with fusion records; these only exist so a garbage table cannot spin. */
#define PSX_FUSION_MAX_EQUIP_GROUPS 256
#define PSX_FUSION_MAX_PAIRS        1024

/* Cached verdict, plus the cheap sentinel it is valid for. Both tables are
 * DUEL data loaded from disc, not part of the EXE image: outside a duel every
 * byte of them reads back as zero. So readiness cannot be latched once and
 * kept -- a stale "ready" would turn "the tables are gone" into the much worse
 * answer "these cards do not fuse". The sentinel below is three halfwords, so
 * re-checking it on every query costs nothing, and the full walk only re-runs
 * when it changes. */
static int s_ready;
static int s_sentinel_ok = -1;

static uint16_t pair_lookup(uint16_t a, uint16_t b)
{
    uint16_t lo = a < b ? a : b;
    uint16_t hi = a < b ? b : a;
    if (lo < 1 || hi > PSX_FUSION_CARD_ID_MAX) return 0;

    uint32_t off = psx_mod_read_half(PSX_FUSION_PAIR_BASE + (uint32_t)lo * 2u);
    if (off < PSX_FUSION_INDEX_BYTES) return 0;

    uint32_t p = PSX_FUSION_PAIR_BASE + off;
    int count = psx_mod_read_byte(p);
    if (count) {
        p += 1u;
    } else {
        count = 511 - psx_mod_read_byte(p + 1u);
        p += 2u;
    }
    if (count <= 0 || count > PSX_FUSION_MAX_PAIRS) return 0;

    for (; count > 0; count -= 2, p += 5u) {
        const uint8_t g0 = psx_mod_read_byte(p);
        if ((((g0 << 8) & 0x300) | psx_mod_read_byte(p + 1u)) == hi)
            return (uint16_t)(((g0 << 6) & 0x300) | psx_mod_read_byte(p + 2u));
        if ((((g0 << 4) & 0x300) | psx_mod_read_byte(p + 3u)) == hi)
            return (uint16_t)(((g0 << 2) & 0x300) | psx_mod_read_byte(p + 4u));
    }
    return 0;
}

/* func_80019A08: is `member` in `key`'s group? Returns `member` if so. */
static uint16_t equip_lookup(uint16_t key, uint16_t member)
{
    uint32_t p = PSX_FUSION_EQUIP_BASE;
    for (int g = 0; g < PSX_FUSION_MAX_EQUIP_GROUPS; g++) {
        const uint16_t k = psx_mod_read_half(p);
        if (k == 0) return 0;
        const uint16_t count = psx_mod_read_half(p + 2u);
        p += 4u;
        if (k != key) { p += (uint32_t)count * 2u; continue; }
        for (uint16_t i = 0; i < count; i++)
            if (psx_mod_read_half(p + (uint32_t)i * 2u) == member) return member;
        return 0;
    }
    return 0;
}

/* Both tables live in the game's data segment, so before the EXE is in place
 * this reads whatever RAM happens to hold. Rather than trust the addresses,
 * check the shape: a real index has hundreds of live entries and every one of
 * them points past the index array itself, and a real equip table opens with a
 * plausible card id and member count. */
static int validate(void)
{
    int live = 0;
    for (int cid = 1; cid <= PSX_FUSION_CARD_ID_MAX; cid++) {
        const uint16_t off = psx_mod_read_half(PSX_FUSION_PAIR_BASE + (uint32_t)cid * 2u);
        if (!off) continue;
        if (off < PSX_FUSION_INDEX_BYTES) return 0;
        live++;
    }
    if (live < 256) return 0;

    const uint16_t key = psx_mod_read_half(PSX_FUSION_EQUIP_BASE);
    const uint16_t cnt = psx_mod_read_half(PSX_FUSION_EQUIP_BASE + 2u);
    if (key < 1 || key > PSX_FUSION_CARD_ID_MAX) return 0;
    if (cnt < 1 || cnt > PSX_FUSION_CARD_ID_MAX) return 0;
    return 1;
}

/* Is the duel data plausibly resident? Three reads, no walk. */
static int sentinel(void)
{
    if (psx_mod_read_half(PSX_FUSION_EQUIP_BASE) - 1u >= PSX_FUSION_CARD_ID_MAX)
        return 0;
    if (psx_mod_read_half(PSX_FUSION_EQUIP_BASE + 2u) - 1u >= PSX_FUSION_CARD_ID_MAX)
        return 0;
    return psx_mod_read_half(PSX_FUSION_PAIR_BASE + 2u * 2u) >= PSX_FUSION_INDEX_BYTES;
}

int psx_fusion_db_ready(void)
{
    const int now = sentinel();
    if (now != s_sentinel_ok) {
        s_sentinel_ok = now;
        s_ready = now ? validate() : 0;
    }
    return s_ready;
}

uint16_t psx_fusion_db_result(uint16_t first, uint16_t second, int *out_kind)
{
    if (out_kind) *out_kind = PSX_FUSION_NONE;
    if (!psx_fusion_db_ready()) return 0;
    if (first < 1 || first > PSX_FUSION_CARD_ID_MAX) return 0;
    if (second < 1 || second > PSX_FUSION_CARD_ID_MAX) return 0;

    uint16_t r = pair_lookup(first, second);
    if (r) {
        if (r > PSX_FUSION_CARD_ID_MAX) return 0;   /* padding entry */
        if (out_kind) *out_kind = PSX_FUSION_PAIR;
        return r;
    }
    /* Equip, in the two orders the caller tries, in that order. */
    if (equip_lookup(second, first)) {
        if (out_kind) *out_kind = PSX_FUSION_EQUIP;
        return first;
    }
    if (equip_lookup(first, second)) {
        if (out_kind) *out_kind = PSX_FUSION_EQUIP;
        return second;
    }
    return 0;
}

/* ---- the card table -------------------------------------------------------
 *
 * 0x801D4244, one 32-bit word per card, indexed by id-1. Read off the routine
 * that fills a card record when a hand is dealt (0x80024A94..0x80024B24),
 * which is also where the record's atk/def come from:
 *
 *     w = u32 at 0x801D4244 + (id - 1) * 4
 *     attack  = (w        & 0x1FF) * 10        `andi 0x1FF` then *5 then *2
 *     defence = ((w >> 9) & 0x1FF) * 10        `sra 9`, same scaling
 *     type    = (w >> 26) & 0x1F               `sra 26`, `andi 0x1F`
 *
 * Attack and defence check out against the GameFAQs password guide on 614 of
 * its 620 listed cards, and every one of the six disagreements is the guide
 * being wrong, not this: Castle of Dark Illusions really is 920/1930, Dragon
 * Zombie really is 1600/0, and Monster Eye's 250/350 was independently
 * confirmed from the game's own hand record earlier. The type code lands 604 of
 * 614 cards in the right group, the strays again being guide errors (one of
 * them spells Insect "Incest").
 *
 * Bits 18..25 are unread here. They are almost certainly the two guardian
 * stars at four bits each, since that is exactly the gap between defence and
 * type — but "almost certainly" is not measured, so nothing depends on it. */
#define PSX_FUSION_STATS_BASE 0x801D4244u

int psx_fusion_db_stats(uint16_t id, int *atk, int *def, int *type)
{
    if (id < 1 || id > PSX_FUSION_CARD_ID_MAX) return 0;
    const uint32_t w =
        psx_mod_read_word(PSX_FUSION_STATS_BASE + ((uint32_t)id - 1u) * 4u);
    if (!w) return 0;               /* table not resident, or no such card */
    if (atk)  *atk  = (int)(w & 0x1FFu) * 10;
    if (def)  *def  = (int)((w >> 9) & 0x1FFu) * 10;
    if (type) *type = (int)((w >> 26) & 0x1Fu);
    return 1;
}

void psx_fusion_db_debug(int *ready, uint32_t *pair_base, uint32_t *equip_base,
                         int *cards_with_fusions, int *pairs,
                         int *equip_groups, int *equip_members)
{
    if (ready)      *ready      = psx_fusion_db_ready();
    if (pair_base)  *pair_base  = PSX_FUSION_PAIR_BASE;
    if (equip_base) *equip_base = PSX_FUSION_EQUIP_BASE;

    if (cards_with_fusions || pairs) {
        int cards = 0, total = 0;
        for (int cid = 1; cid <= PSX_FUSION_CARD_ID_MAX; cid++) {
            const uint16_t off =
                psx_mod_read_half(PSX_FUSION_PAIR_BASE + (uint32_t)cid * 2u);
            if (off < PSX_FUSION_INDEX_BYTES) continue;
            cards++;
            const uint32_t p = PSX_FUSION_PAIR_BASE + off;
            const uint8_t b0 = psx_mod_read_byte(p);
            total += b0 ? b0 : (511 - psx_mod_read_byte(p + 1u));
        }
        if (cards_with_fusions) *cards_with_fusions = cards;
        if (pairs)              *pairs              = total;
    }

    if (equip_groups || equip_members) {
        int groups = 0, members = 0;
        uint32_t p = PSX_FUSION_EQUIP_BASE;
        for (int g = 0; g < PSX_FUSION_MAX_EQUIP_GROUPS; g++) {
            if (psx_mod_read_half(p) == 0) break;
            const uint16_t count = psx_mod_read_half(p + 2u);
            groups++;
            members += count;
            p += 4u + (uint32_t)count * 2u;
        }
        if (equip_groups)  *equip_groups  = groups;
        if (equip_members) *equip_members = members;
    }
}
