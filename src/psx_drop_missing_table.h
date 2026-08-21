/* psx_drop_missing_table.h -- GENERATED, do not hand-edit.
 *
 * Default placements for MODS > DROP MISSING CARDS, plus one fingerprint per
 * duelist so the running game can be identified from its resident drop data.
 * Regenerate with tools/gen_drop_table.py.
 */
#ifndef PSX_DROP_MISSING_TABLE_H
#define PSX_DROP_MISSING_TABLE_H

#include <stdint.h>

typedef struct { uint16_t card; uint8_t tier; uint16_t weight; } PsxDropAdd;
typedef struct {
    const char       *name;
    uint32_t          fingerprint;   /* FNV-1a over deck + 3 drop tiers */
    const PsxDropAdd *adds;
    uint8_t           n_adds;
} PsxDropDuelist;

static const PsxDropAdd PSX_DROP_D00[] = {   /* Simon Muran */
    { 628, 0,  40 },   /* S/A POW   Witch's Apprentice             */
    { 541, 0,  30 },   /* S/A POW   Hane-Hane                      */
    {  17, 0,  20 },   /* S/A POW   Right Leg of the Forbidden One */
    { 628, 1,  20 },   /* B/C/D     Witch's Apprentice             */
    { 541, 1,  20 },   /* B/C/D     Hane-Hane                      */
};
static const PsxDropAdd PSX_DROP_D01[] = {   /* Teana */
    { 363, 0,  40 },   /* S/A POW   Fairy's Gift                   */
    { 354, 0,  40 },   /* S/A POW   Stuffed Animal                 */
    { 429, 0,  40 },   /* S/A POW   Goddess of Whim                */
    { 363, 1,  20 },   /* B/C/D     Fairy's Gift                   */
    { 354, 1,  20 },   /* B/C/D     Stuffed Animal                 */
    { 429, 1,  20 },   /* B/C/D     Goddess of Whim                */
};
static const PsxDropAdd PSX_DROP_D02[] = {   /* Jono */
    {   7, 0,  40 },   /* S/A POW   Winged Dragon #1               */
    { 603, 0,  40 },   /* S/A POW   Fairy Dragon                   */
    {   7, 1,  20 },   /* B/C/D     Winged Dragon #1               */
    { 603, 1,  20 },   /* B/C/D     Fairy Dragon                   */
};
static const PsxDropAdd PSX_DROP_D03[] = {   /* Villager1 */
    { 489, 0,  40 },   /* S/A POW   Barrel Lily                    */
    { 489, 1,  20 },   /* B/C/D     Barrel Lily                    */
};
static const PsxDropAdd PSX_DROP_D04[] = {   /* Villager2 */
    { 235, 0,  40 },   /* S/A POW   Wodan the Resident of the Forest */
    { 235, 1,  20 },   /* B/C/D     Wodan the Resident of the Forest */
};
static const PsxDropAdd PSX_DROP_D05[] = {   /* Villager3 */
    { 359, 0,  40 },   /* S/A POW   Three-legged Zombies           */
    { 359, 1,  20 },   /* B/C/D     Three-legged Zombies           */
};
static const PsxDropAdd PSX_DROP_D06[] = {   /* Seto */
    { 428, 0,  40 },   /* S/A POW   Magician of Faith              */
    { 644, 0,  30 },   /* S/A POW   Flame Viper                    */
    {  18, 0,  20 },   /* S/A POW   Left Leg of the Forbidden One  */
    { 644, 1,  20 },   /* B/C/D     Flame Viper                    */
    { 428, 1,  20 },   /* B/C/D     Magician of Faith              */
};
static const PsxDropAdd PSX_DROP_D07[] = {   /* Heishin */
    {  22, 0,  20 },   /* S/A POW   Summoned Skull                 */
    { 669, 2,  64 },   /* S/A TEC   Shadow Spell                   */
};
static const PsxDropAdd PSX_DROP_D08[] = {   /* Rex Raptor */
    {  51, 0,  30 },   /* S/A POW   Armored Lizard                 */
};
static const PsxDropAdd PSX_DROP_D09[] = {   /* Weevil Underwood */
    { 278, 0,  30 },   /* S/A POW   Petit Moth                     */
    { 499, 0,  30 },   /* S/A POW   Kattapillar                    */
    {  56, 0,  20 },   /* S/A POW   Larvae Moth                    */
    {  72, 0,  15 },   /* S/A POW   Cocoon of Evolution            */
    {  56, 1,  20 },   /* B/C/D     Larvae Moth                    */
    { 278, 1,  20 },   /* B/C/D     Petit Moth                     */
    { 499, 1,  20 },   /* B/C/D     Kattapillar                    */
    { 696, 2,  64 },   /* S/A TEC   Javelin Beetle Pact            */
};
static const PsxDropAdd PSX_DROP_D10[] = {   /* Mai Valentine */
    {  62, 0,  40 },   /* S/A POW   Harpie Lady                    */
    {  63, 0,  20 },   /* S/A POW   Harpie Lady Sisters            */
    {  62, 1,  20 },   /* B/C/D     Harpie Lady                    */
    { 318, 1,  20 },   /* B/C/D     Elegant Egotist                */
};
static const PsxDropAdd PSX_DROP_D11[] = {   /* Bandit Keith */
    { 537, 0,  40 },   /* S/A POW   Mega Thunderball               */
    { 355, 0,  30 },   /* S/A POW   Megasonic Eye                  */
    { 537, 1,  20 },   /* B/C/D     Mega Thunderball               */
};
static const PsxDropAdd PSX_DROP_D12[] = {   /* Shadi */
    { 361, 0,  40 },   /* S/A POW   Flying Penguin                 */
    { 252, 0,  40 },   /* S/A POW   Nekogal #1                     */
    { 288, 0,  40 },   /* S/A POW   Dark Artist                    */
    { 361, 1,  20 },   /* B/C/D     Flying Penguin                 */
    { 252, 1,  20 },   /* B/C/D     Nekogal #1                     */
    { 288, 1,  20 },   /* B/C/D     Dark Artist                    */
};
static const PsxDropAdd PSX_DROP_D13[] = {   /* Yami Bakura */
    { 719, 0,  30 },   /* S/A POW   Dokurorider                    */
    { 545, 0,  30 },   /* S/A POW   Skelgon                        */
    { 369, 0,  30 },   /* S/A POW   Wall Shadow                    */
    { 670, 2,  64 },   /* S/A TEC   Black Luster Ritual            */
};
static const PsxDropAdd PSX_DROP_D14[] = {   /* Pegasus */
    { 284, 0,  40 },   /* S/A POW   Tao the Chanter                */
    { 357, 0,  30 },   /* S/A POW   Yamadron                       */
    { 284, 1,  20 },   /* B/C/D     Tao the Chanter                */
};
static const PsxDropAdd PSX_DROP_D15[] = {   /* Isis */
    { 701, 0,  30 },   /* S/A POW   Performance of Sword           */
    { 555, 0,  30 },   /* S/A POW   Tyhone #2                      */
    { 715, 0,  20 },   /* S/A POW   Psycho-Puppet                  */
};
static const PsxDropAdd PSX_DROP_D16[] = {   /* Kaiba */
    { 299, 0,  40 },   /* S/A POW   Sonic Maid                     */
    {  60, 0,  30 },   /* S/A POW   Great White                    */
    { 299, 1,  20 },   /* B/C/D     Sonic Maid                     */
};
static const PsxDropAdd PSX_DROP_D17[] = {   /* Mage Soldier */
    { 353, 0,  40 },   /* S/A POW   Takriminos                     */
    {  28, 0,  40 },   /* S/A POW   Rock Ogre Grotto #1            */
    { 353, 1,  20 },   /* B/C/D     Takriminos                     */
    {  28, 1,  20 },   /* B/C/D     Rock Ogre Grotto #1            */
    { 689, 2,  64 },   /* S/A TEC   Reverse Trap                   */
};
static const PsxDropAdd PSX_DROP_D18[] = {   /* Jono 2nd */
    {  69, 0,  10 },   /* S/A POW   Thousand Dragon                */
};
static const PsxDropAdd PSX_DROP_D19[] = {   /* Teana 2nd */
    { 554, 0,  30 },   /* S/A POW   Lava Battleguard               */
};
static const PsxDropAdd PSX_DROP_D20[] = {   /* Ocean Mage */
    { 352, 0,  40 },   /* S/A POW   Kanan the Swordmistress        */
    { 352, 1,  20 },   /* B/C/D     Kanan the Swordmistress        */
};
static const PsxDropAdd PSX_DROP_D21[] = {   /* High Mage Secmeton */
    { 710, 0,  20 },   /* S/A POW   Crab Turtle                    */
    { 718, 0,  20 },   /* S/A POW   Fortress Whale                 */
};
static const PsxDropAdd PSX_DROP_D22[] = {   /* Forest Mage */
    { 709, 0,  20 },   /* S/A POW   Chakra                         */
    { 702, 0,  20 },   /* S/A POW   Hungry Burger                  */
    {  57, 0,  10 },   /* S/A POW   Great Moth                     */
};
static const PsxDropAdd PSX_DROP_D23[] = {   /* High Mage Anubisius */
    { 717, 0,  20 },   /* S/A POW   Javelin Beetle                 */
    {  67, 0,  10 },   /* S/A POW   Perfectly Ultimate Great Moth  */
};
static const PsxDropAdd PSX_DROP_D24[] = {   /* Mountain Mage */
    {  37, 0,  20 },   /* S/A POW   Gaia the Dragon Champion       */
    { 358, 0,  20 },   /* S/A POW   Seiyaryu                       */
};
static const PsxDropAdd PSX_DROP_D25[] = {   /* High Mage Atenza */
    { 705, 0,  20 },   /* S/A POW   Tri-horned Dragon              */
    { 217, 0,  10 },   /* S/A POW   B. Skull Dragon                */
};
static const PsxDropAdd PSX_DROP_D26[] = {   /* Desert Mage */
    { 711, 0,  20 },   /* S/A POW   Mikazukinoyaiba                */
    { 704, 0,  20 },   /* S/A POW   Skull Guardian                 */
    { 360, 0,  10 },   /* S/A POW   Zera The Mant                  */
};
static const PsxDropAdd PSX_DROP_D27[] = {   /* High Mage Martis */
    { 706, 0,  20 },   /* S/A POW   Serpent Night Dragon           */
    { 356, 0,  20 },   /* S/A POW   Super War-lion                 */
    { 720, 0,  20 },   /* S/A POW   Mask of Shine & Dark           */
};
static const PsxDropAdd PSX_DROP_D28[] = {   /* Meadow Mage */
    { 365, 0,  20 },   /* S/A POW   Fiend's Mirror                 */
    { 722, 0,  10 },   /* S/A POW   Magician of Black Chaos        */
    { 703, 0,  10 },   /* S/A POW   Sengenjin                      */
    { 362, 0,  10 },   /* S/A POW   Millennium Shield              */
};
static const PsxDropAdd PSX_DROP_D29[] = {   /* High Mage Kepura */
    { 716, 0,  20 },   /* S/A POW   Garma Sword                    */
    {  92, 0,  20 },   /* S/A POW   Rabid Horseman                 */
    { 364, 0,  10 },   /* S/A POW   Black Luster Soldier           */
};
static const PsxDropAdd PSX_DROP_D30[] = {   /* Labyrinth Mage */
    { 374, 0,  10 },   /* S/A POW   Gate Guardian                  */
    { 667, 1,  20 },   /* B/C/D     Gate Guardian Ritual           */
};
static const PsxDropAdd PSX_DROP_D31[] = {   /* Seto 2nd */
    { 721, 2,  64 },   /* S/A TEC   Dark Magic Ritual              */
    { 348, 2,  48 },   /* S/A TEC   Swords of Revealing Light      */
};
static const PsxDropAdd PSX_DROP_D32[] = {   /* Guardian Sebek */
    { 351, 0,  40 },   /* S/A POW   Yaranzo                        */
    { 351, 1,  20 },   /* B/C/D     Yaranzo                        */
};
static const PsxDropAdd PSX_DROP_D33[] = {   /* Guardian Neku */
    { 562, 0,  20 },   /* S/A POW   Needle Worm                    */
    { 562, 1,  20 },   /* B/C/D     Needle Worm                    */
};
static const PsxDropAdd PSX_DROP_D34[] = {   /* Heishin 2nd */
    { 708, 0,  20 },   /* S/A POW   Cosmo Queen                    */
};
static const PsxDropAdd PSX_DROP_D35[] = {   /* Seto 3rd */
    { 380, 0,  10 },   /* S/A POW   Blue-eyes Ultimate Dragon      */
};
static const PsxDropAdd PSX_DROP_D36[] = {   /* DarkNite */
    {  64, 0,  40 },   /* S/A POW   Tiger Axe                      */
    {  64, 1,  20 },   /* B/C/D     Tiger Axe                      */
};
static const PsxDropAdd PSX_DROP_D37[] = {   /* Nitemare */
    { 640, 0,  30 },   /* S/A POW   Acid Crawler                   */
    { 640, 1,  20 },   /* B/C/D     Acid Crawler                   */
};
static const PsxDropAdd PSX_DROP_D38[] = {   /* Duel Master K */
    {  52, 0,  30 },   /* S/A POW   Hercules Beetle                */
};

typedef struct { uint16_t card; const char *name; } PsxDropName;
static const PsxDropName PSX_DROP_NAMES[] = {
    {   7, "Winged Dragon #1" },
    {  17, "Right Leg of the Forbidden One" },
    {  18, "Left Leg of the Forbidden One" },
    {  22, "Summoned Skull" },
    {  28, "Rock Ogre Grotto #1" },
    {  37, "Gaia the Dragon Champion" },
    {  51, "Armored Lizard" },
    {  52, "Hercules Beetle" },
    {  56, "Larvae Moth" },
    {  57, "Great Moth" },
    {  60, "Great White" },
    {  62, "Harpie Lady" },
    {  63, "Harpie Lady Sisters" },
    {  64, "Tiger Axe" },
    {  67, "Perfectly Ultimate Great Moth" },
    {  69, "Thousand Dragon" },
    {  72, "Cocoon of Evolution" },
    {  92, "Rabid Horseman" },
    { 217, "B. Skull Dragon" },
    { 235, "Wodan the Resident of the Forest" },
    { 252, "Nekogal #1" },
    { 278, "Petit Moth" },
    { 284, "Tao the Chanter" },
    { 288, "Dark Artist" },
    { 299, "Sonic Maid" },
    { 318, "Elegant Egotist" },
    { 348, "Swords of Revealing Light" },
    { 351, "Yaranzo" },
    { 352, "Kanan the Swordmistress" },
    { 353, "Takriminos" },
    { 354, "Stuffed Animal" },
    { 355, "Megasonic Eye" },
    { 356, "Super War-lion" },
    { 357, "Yamadron" },
    { 358, "Seiyaryu" },
    { 359, "Three-legged Zombies" },
    { 360, "Zera The Mant" },
    { 361, "Flying Penguin" },
    { 362, "Millennium Shield" },
    { 363, "Fairy's Gift" },
    { 364, "Black Luster Soldier" },
    { 365, "Fiend's Mirror" },
    { 369, "Wall Shadow" },
    { 374, "Gate Guardian" },
    { 380, "Blue-eyes Ultimate Dragon" },
    { 428, "Magician of Faith" },
    { 429, "Goddess of Whim" },
    { 489, "Barrel Lily" },
    { 499, "Kattapillar" },
    { 537, "Mega Thunderball" },
    { 541, "Hane-Hane" },
    { 545, "Skelgon" },
    { 554, "Lava Battleguard" },
    { 555, "Tyhone #2" },
    { 562, "Needle Worm" },
    { 603, "Fairy Dragon" },
    { 628, "Witch's Apprentice" },
    { 640, "Acid Crawler" },
    { 644, "Flame Viper" },
    { 667, "Gate Guardian Ritual" },
    { 669, "Shadow Spell" },
    { 670, "Black Luster Ritual" },
    { 689, "Reverse Trap" },
    { 696, "Javelin Beetle Pact" },
    { 701, "Performance of Sword" },
    { 702, "Hungry Burger" },
    { 703, "Sengenjin" },
    { 704, "Skull Guardian" },
    { 705, "Tri-horned Dragon" },
    { 706, "Serpent Night Dragon" },
    { 708, "Cosmo Queen" },
    { 709, "Chakra" },
    { 710, "Crab Turtle" },
    { 711, "Mikazukinoyaiba" },
    { 715, "Psycho-Puppet" },
    { 716, "Garma Sword" },
    { 717, "Javelin Beetle" },
    { 718, "Fortress Whale" },
    { 719, "Dokurorider" },
    { 720, "Mask of Shine & Dark" },
    { 721, "Dark Magic Ritual" },
    { 722, "Magician of Black Chaos" },
};
#define PSX_DROP_NAME_COUNT 82

static const PsxDropDuelist PSX_DROP_DUELISTS[39] = {
    { "Simon Muran", 0xEA66C91Du, PSX_DROP_D00, 5 },
    { "Teana", 0x58590C6Bu, PSX_DROP_D01, 6 },
    { "Jono", 0xAE2BF0FDu, PSX_DROP_D02, 4 },
    { "Villager1", 0x747C89DBu, PSX_DROP_D03, 2 },
    { "Villager2", 0x3AB8CA8Fu, PSX_DROP_D04, 2 },
    { "Villager3", 0x564C188Bu, PSX_DROP_D05, 2 },
    { "Seto", 0xC97193A9u, PSX_DROP_D06, 5 },
    { "Heishin", 0x15D176C1u, PSX_DROP_D07, 2 },
    { "Rex Raptor", 0xA8B325CBu, PSX_DROP_D08, 1 },
    { "Weevil Underwood", 0xAC9B3A61u, PSX_DROP_D09, 8 },
    { "Mai Valentine", 0xE34F9A67u, PSX_DROP_D10, 4 },
    { "Bandit Keith", 0xE4D7E6F7u, PSX_DROP_D11, 3 },
    { "Shadi", 0xBE3EB2B3u, PSX_DROP_D12, 6 },
    { "Yami Bakura", 0xD65F3BA1u, PSX_DROP_D13, 4 },
    { "Pegasus", 0x1B12CA2Du, PSX_DROP_D14, 3 },
    { "Isis", 0x3F823DE9u, PSX_DROP_D15, 3 },
    { "Kaiba", 0x2467B207u, PSX_DROP_D16, 3 },
    { "Mage Soldier", 0x215F3093u, PSX_DROP_D17, 5 },
    { "Jono 2nd", 0x220B0061u, PSX_DROP_D18, 1 },
    { "Teana 2nd", 0x76F5A2C1u, PSX_DROP_D19, 1 },
    { "Ocean Mage", 0x52C017C1u, PSX_DROP_D20, 2 },
    { "High Mage Secmeton", 0x454A9721u, PSX_DROP_D21, 2 },
    { "Forest Mage", 0xB99110C1u, PSX_DROP_D22, 3 },
    { "High Mage Anubisius", 0xEA2F4EBBu, PSX_DROP_D23, 2 },
    { "Mountain Mage", 0x45998A0Fu, PSX_DROP_D24, 2 },
    { "High Mage Atenza", 0x1FB2561Fu, PSX_DROP_D25, 2 },
    { "Desert Mage", 0x55F16F75u, PSX_DROP_D26, 3 },
    { "High Mage Martis", 0x9B59AF6Bu, PSX_DROP_D27, 3 },
    { "Meadow Mage", 0xA8A26509u, PSX_DROP_D28, 4 },
    { "High Mage Kepura", 0xBD14DA8Du, PSX_DROP_D29, 3 },
    { "Labyrinth Mage", 0x71E33049u, PSX_DROP_D30, 2 },
    { "Seto 2nd", 0x6139F8D3u, PSX_DROP_D31, 2 },
    { "Guardian Sebek", 0xBAB01EF9u, PSX_DROP_D32, 2 },
    { "Guardian Neku", 0x09D00161u, PSX_DROP_D33, 2 },
    { "Heishin 2nd", 0x7B0E6071u, PSX_DROP_D34, 1 },
    { "Seto 3rd", 0xD6BCA14Du, PSX_DROP_D35, 1 },
    { "DarkNite", 0x1E12592Fu, PSX_DROP_D36, 2 },
    { "Nitemare", 0x3FAEF4EDu, PSX_DROP_D37, 2 },
    { "Duel Master K", 0x95F0E81Bu, PSX_DROP_D38, 1 },
};

/* The four weight arrays the game leaves resident for the current opponent:
 * deck pool first, then drop tiers 0..2, 722 u16 each, stride 1460 bytes. */
#define PSX_DROP_RESIDENT_BASE  0x801781D8u
#define PSX_DROP_TABLE_STRIDE   1460u
#define PSX_DROP_CARDS          722u
#define PSX_DROP_TIER_TOTAL     2048u

#endif /* PSX_DROP_MISSING_TABLE_H */
