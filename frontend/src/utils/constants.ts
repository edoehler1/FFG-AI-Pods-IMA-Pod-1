export const INDUSTRY_LABELS: Record<string, string> = {
  automotive: 'Automotive',
  aerospace_defense: 'Aerospace & Defense',
  energy: 'Energy',
};

export const INDUSTRY_LABELS_SHORT: Record<string, string> = {
  automotive: 'Auto',
  aerospace_defense: 'A&D',
  energy: 'Energy',
};

export const SUB_SECTORS: Record<string, { value: string; label: string }[]> = {
  automotive: [
    { value: 'oem', label: 'OEMs' },
    { value: 'ev', label: 'EV' },
    { value: 'tier1_supplier', label: 'Tier 1 Suppliers' },
    { value: 'aftermarket', label: 'Aftermarket' },
  ],
  aerospace_defense: [
    { value: 'defense_prime', label: 'Defense Primes' },
    { value: 'defense_electronics', label: 'Defense Electronics' },
    { value: 'commercial_aerospace', label: 'Commercial Aerospace' },
    { value: 'space', label: 'Space' },
  ],
  energy: [
    { value: 'upstream', label: 'Upstream' },
    { value: 'midstream', label: 'Midstream' },
    { value: 'downstream', label: 'Downstream' },
    { value: 'renewables', label: 'Renewables' },
    { value: 'utilities', label: 'Utilities' },
    { value: 'nuclear', label: 'Nuclear' },
  ],
};

export const COMPANY_SIZES: { value: string; label: string }[] = [
  { value: 'mega_cap', label: 'Mega-cap ($50B+)' },
  { value: 'large_cap', label: 'Large-cap ($10B–$50B)' },
  { value: 'mid_cap', label: 'Mid-cap ($1B–$10B)' },
  { value: 'small_cap', label: 'Small-cap (<$1B)' },
];

export const SIZE_LABELS: Record<string, string> = Object.fromEntries(
  COMPANY_SIZES.map((s) => [s.value, s.label])
);
