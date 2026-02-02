export interface Candidate {
	state: string;
	office: string;
	district: string;
	candidate: string;
	party: string;
	unopposed_in: string;
	source: string;
}

export interface GeneralStats {
	total_unopposed: number;
	total_races: number;
	unopposed_by_party: Record<string, number>;
}

export interface PrimaryStats {
	total_unopposed: number;
	total_races_by_party: Record<string, number>;
	unopposed_by_party: Record<string, number>;
}

export interface ElectionData {
	state: string;
	state_name: string;
	year: number;
	total: number;
	total_races: number;
	total_races_by_party: Record<string, number>;
	general?: GeneralStats;
	primary?: PrimaryStats;
	scraped_at: string;
	unopposed_candidates: Candidate[];
}

export interface StateInfo {
	code: string;
	name: string;
	filename: string;
}

export interface NationwideStats {
	general: GeneralStats;
	primary: PrimaryStats;
}

export interface Manifest {
	years: number[];
	updated_at: string;
	nationwide?: Record<string, NationwideStats>;
}

export const STATE_NAMES: Record<string, string> = {
	AL: 'Alabama',
	AK: 'Alaska',
	AZ: 'Arizona',
	AR: 'Arkansas',
	CA: 'California',
	CO: 'Colorado',
	CT: 'Connecticut',
	DE: 'Delaware',
	FL: 'Florida',
	GA: 'Georgia',
	HI: 'Hawaii',
	ID: 'Idaho',
	IL: 'Illinois',
	IN: 'Indiana',
	IA: 'Iowa',
	KS: 'Kansas',
	KY: 'Kentucky',
	LA: 'Louisiana',
	ME: 'Maine',
	MD: 'Maryland',
	MA: 'Massachusetts',
	MI: 'Michigan',
	MN: 'Minnesota',
	MS: 'Mississippi',
	MO: 'Missouri',
	MT: 'Montana',
	NE: 'Nebraska',
	NV: 'Nevada',
	NH: 'New Hampshire',
	NJ: 'New Jersey',
	NM: 'New Mexico',
	NY: 'New York',
	NC: 'North Carolina',
	ND: 'North Dakota',
	OH: 'Ohio',
	OK: 'Oklahoma',
	OR: 'Oregon',
	PA: 'Pennsylvania',
	RI: 'Rhode Island',
	SC: 'South Carolina',
	SD: 'South Dakota',
	TN: 'Tennessee',
	TX: 'Texas',
	UT: 'Utah',
	VT: 'Vermont',
	VA: 'Virginia',
	WA: 'Washington',
	WV: 'West Virginia',
	WI: 'Wisconsin',
	WY: 'Wyoming',
	DC: 'District of Columbia'
};

export const STATE_CODES = Object.keys(STATE_NAMES);

export function getFilename(stateCode: string): string {
	return STATE_NAMES[stateCode].toLowerCase().replace(/ /g, '_');
}

export function getDefaultYear(): number {
	return new Date().getFullYear();
}
