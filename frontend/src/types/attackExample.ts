// types/attackExample.ts

export interface AttackExampleTechnique {
    technique_id: string;
    technique_name: string;
    technique_parent: string;
    usage_description?: string;
    selected_tactic?: string;
    selected_kill_chain_phase?: string;
    mitigations?: {
        name: string;
        description: string;
    }[];
}
