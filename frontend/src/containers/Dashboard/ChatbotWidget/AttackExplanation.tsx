import * as Tabs from "@radix-ui/react-tabs";
import KillChainPhaseOverview from "./KillChainPhaseOverview.tsx";
import type {Campaign} from "../../../types/campaign.ts";
import type {ReferenceTag} from "../../../types/reference.ts";

export type KillChainPhase = "In" | "Through" | "Out";


const KILL_CHAIN_PHASES: {
    value: KillChainPhase;
    label: string;
}[] = [
    {value: "In", label: "In (Initial Foothold)"},
    {value: "Through", label: "Through (Network Propagation)"},
    {value: "Out", label: "Out (Action on Objectives)"},
];

interface AttackExplanationProps {
    campaign?: Campaign | null | undefined
    onTacticShown: (tacticName: string) => void;
    onInsertReference: (ref: ReferenceTag) => void;
}

export default function AttackExplanation({campaign, onTacticShown, onInsertReference}: AttackExplanationProps) {

    return (
        <div className="flex flex-col flex-1 min-h-0">
            <Tabs.Root defaultValue="In" className="flex flex-col flex-1">
                <Tabs.List className="flex border-b border-gray-300 mb-4">
                    {KILL_CHAIN_PHASES.map((phase) => (
                        <Tabs.Trigger
                            key={phase.value}
                            value={phase.value}
                            className="data-[state=active]:text-blue-600"
                        >
                            {phase.label}
                        </Tabs.Trigger>
                    ))}
                </Tabs.List>

                {KILL_CHAIN_PHASES.map((phase) => (
                    <Tabs.Content
                        key={phase.value}
                        value={phase.value}
                        className="p-4 border rounded-b-lg border-gray-300"
                    >
                        {campaign && (
                            <KillChainPhaseOverview
                                key={`${campaign?.id}-${phase}`}
                                campaign={campaign}
                                phase={phase.value}
                                onTacticShown={onTacticShown}
                                onInsertReference={onInsertReference}
                            />
                        )}
                    </Tabs.Content>
                ))}
            </Tabs.Root>
        </div>
    );
}