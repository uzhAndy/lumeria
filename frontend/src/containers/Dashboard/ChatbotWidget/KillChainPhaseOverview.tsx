import {useEffect, useRef, useState, Fragment} from "react";
import type { Campaign } from "../../../types/campaign.ts";
import type { KillChainPhase } from "./AttackExplanation.tsx";
import type { AttackExampleTechnique } from "../../../types/attackExample.ts";
import { Button } from "@radix-ui/themes";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import type {ReferenceTag} from "../../../types/reference.ts";
import { Search } from "lucide-react";
import * as Tooltip from "@radix-ui/react-tooltip";

interface KillChainPhaseOverviewProps {
    campaign: Campaign;
    phase: KillChainPhase;
    onTacticShown: (tacticName: string) => void;
    onInsertReference: (ref: ReferenceTag) => void;
}

const phaseDescriptions: Record<KillChainPhase, string> = {
    In: "The phase where an attacker gains initial access to an environment, such as by exploiting a vulnerability, using stolen credentials or tricking a user into granting access.",
    Through: "The phase where the attacker operates within the environment, moving between systems, escalating privileges (such as going from a normal user account to an administrator), and achieving their objectives.",
    Out: "The phase where the attacker completes their activity, often by extracting data, maintaining persistence, or attempting to hide evidence of the intrusion.",
};

export default function KillChainPhaseOverview({
                                                   campaign,
                                                   phase,
                                                   onTacticShown,
                                                   onInsertReference,
                                               }: KillChainPhaseOverviewProps) {
    const [attackExample, setAttackExample] = useState<
        { tactic: string; phase: KillChainPhase; techniques: AttackExampleTechnique[] }[]
    >([]);
    const [currentTacticIndex, setCurrentTacticIndex] = useState(0);
    const [showMitigations, setShowMitigations] = useState(false);
    const firstExplanationSentRef = useRef(false);
    const fetchedTechniquesRef = useRef(false);

    useEffect(() => {
        if (!campaign) return;
        if (fetchedTechniquesRef.current) return; // Exit if already called (needed because in dev mode every call is made twice)

        const fetchTechniques = async () => {
            // Returns a list of tactics and their techniques, already ordered according to the kill chain progression.
            // Techniques within each tactic are sorted so that parent techniques appear immediately before their children.
            const res = await fetch(
                `http://localhost:8000/api/campaigns/${campaign.id}/attack-example/?phase=${phase}`
            );
            console.log(res);
            if (!res.ok) return;

            fetchedTechniquesRef.current = true;

            const data = await res.json();
            const example = data.attack_example || [];
            console.log("Attack Example: ", example);
            setAttackExample(example || []);
            setCurrentTacticIndex(0);
            if (example.length > 0 && !firstExplanationSentRef.current) {
                firstExplanationSentRef.current = true;
                onTacticShown(example[0].tactic);
            }
        };

        fetchTechniques().catch(console.error);
    }, [campaign?.id, phase]);

    const visibleTactics = attackExample.slice(0, currentTacticIndex + 1);

    if (attackExample.length === 0) {
        return (
            <p className="text-sm text-gray-500">
                No techniques recorded for this campaign.
            </p>
        );
    }

    const goToNextTactic = () => {
        const nextIndex = currentTacticIndex + 1;
        const nextTactic = attackExample[nextIndex];
        if (!nextTactic) return;

        setCurrentTacticIndex(nextIndex);
        onTacticShown(nextTactic.tactic);
    };

    return (
        <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-0">
                <h3 className="font-semibold text-gray-700">
                    Techniques observed in the <b>{phase}</b> phase
                </h3>
                <p className="text-sm text-gray-600 text-left">
                    {phaseDescriptions[phase]}
                </p>
            </div>

            <div className="flex flex-col gap-3">
                {visibleTactics.map((tactic, index) => (
                    <Fragment key={tactic.tactic}>
                        <div
                            className="grid grid-cols-[200px_1fr] gap-4 rounded-lg border bg-white shadow-sm p-4"
                        >
                            <div className="flex items-start">
                                <div className="flex gap-3 items-center rounded-md bg-blue-100 text-blue-800 px-3 py-2">
                                    <span className="text-sm font-semibold">
                                    {tactic.tactic.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                    </span>
                                    <Tooltip.Provider>
                                        <Tooltip.Root>
                                            <Tooltip.Trigger asChild>
                                                <Button
                                                    size="2"
                                                    variant="ghost"
                                                    onClick={() =>
                                                        onInsertReference({
                                                            type: "tactic",
                                                            label: tactic.tactic,
                                                        })
                                                    }
                                                >
                                                    <Search size={14} />
                                                </Button>
                                            </Tooltip.Trigger>

                                            <Tooltip.Portal>
                                                <Tooltip.Content
                                                    side="top"
                                                    align="center"
                                                    className="bg-white rounded px-2 py-1 text-xs border border-gray-400"
                                                >
                                                    Ask the Chatbot about this tactic
                                                </Tooltip.Content>
                                            </Tooltip.Portal>
                                        </Tooltip.Root>
                                    </Tooltip.Provider>
                                </div>
                            </div>

                            <div className="flex flex-col gap-2">
                                {tactic.techniques.map((tech) => (
                                    <div
                                        key={tech.technique_id}
                                        className="rounded-md bg-gray-50 border p-3"
                                    >
                                        <div className="flex items-center">
                                            <div className="flex-1 text-center text-sm font-medium text-gray-800">
                                                {tech.technique_parent ? (
                                                    <>
                                                        {tech.technique_parent} - <span className="italic text-blue-800">{tech.technique_name}</span>
                                                    </>
                                                ) : (
                                                    <>{tech.technique_name}</>
                                                )}
                                            </div>
                                            <Tooltip.Provider>
                                                <Tooltip.Root>
                                                    <Tooltip.Trigger asChild>
                                                        <Button
                                                            size="1"
                                                            variant="ghost"
                                                            onClick={() =>
                                                                onInsertReference({
                                                                    type: "technique",
                                                                    label: tech.technique_name,
                                                                })
                                                            }
                                                        >
                                                            <Search size={14} />
                                                        </Button>
                                                    </Tooltip.Trigger>

                                                    <Tooltip.Portal>
                                                        <Tooltip.Content
                                                            side="top"
                                                            align="center"
                                                            className="bg-white rounded px-2 py-1 text-xs border border-gray-400"
                                                        >
                                                            Ask the chatbot about this technique
                                                        </Tooltip.Content>
                                                    </Tooltip.Portal>
                                                </Tooltip.Root>
                                            </Tooltip.Provider>
                                        </div>
                                        <div className="text-xs text-gray-600 mt-1">
                                            {tech.usage_description}
                                        </div>
                                        {/* Shows mitigations if the mitigation button has been clicked */}
                                        {showMitigations && tech.mitigations && tech.mitigations.length > 0 && (
                                            <div className="mt-2 flex flex-col gap-1">
                                                {tech.mitigations.map((mitigation, index) => (
                                                    <div
                                                        key={index}
                                                        className="rounded-md bg-green-50 border border-green-800 p-2 text-xs"
                                                    >
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex-1 text-center font-semibold text-green-800">
                                                                {mitigation.name}
                                                            </div>
                                                            <Tooltip.Provider>
                                                                <Tooltip.Root>
                                                                    <Tooltip.Trigger asChild>
                                                                        <Button
                                                                            size="1"
                                                                            color={"grass"}
                                                                            variant="ghost"
                                                                            onClick={() =>
                                                                                onInsertReference({
                                                                                    type: "mitigation",
                                                                                    label: mitigation.name,
                                                                                })
                                                                            }
                                                                        >
                                                                            <Search size={14} />
                                                                        </Button>
                                                                    </Tooltip.Trigger>

                                                                    <Tooltip.Portal>
                                                                        <Tooltip.Content
                                                                            side="top"
                                                                            align="center"
                                                                            className="bg-white rounded px-2 py-1 text-xs border border-gray-400"
                                                                        >
                                                                            Ask the chatbot about this mitigation
                                                                        </Tooltip.Content>
                                                                    </Tooltip.Portal>
                                                                </Tooltip.Root>
                                                            </Tooltip.Provider>
                                                        </div>
                                                        <div className="text-gray-600 text-left prose max-w-none">
                                                            <ReactMarkdown rehypePlugins={[rehypeSanitize]}>
                                                                {mitigation.description}
                                                            </ReactMarkdown>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Path Arrow (will only be shown if there is a next tactic in the visible list= */}
                        {index < visibleTactics.length - 1 && (
                            <div className="flex justify-center py-1">
                                <div className="flex flex-col items-center">
                                    <div className="h-2.5 w-0.5 bg-blue-200"></div>
                                    <svg
                                        width="30"
                                        height="30"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="3"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        className="text-blue-400"
                                    >
                                        <path d="M7 13l5 5 5-5M12 6v12"/>
                                    </svg>
                                    <div className="h-2.5 w-0.5 bg-blue-200"></div>
                                </div>
                            </div>
                        )}
                    </Fragment>
                ))}
            </div>

            <div className="flex justify-end pt-2">
                <div className="inline-flex flex-col gap-2">
                    <Button
                        onClick={goToNextTactic}
                        disabled={currentTacticIndex === attackExample.length - 1}
                    >
                        Go to Next Tactic
                    </Button>

                    <Button
                        variant="soft"
                        onClick={() => setShowMitigations(prev => !prev)}
                    >
                        {showMitigations ? "Hide Mitigation Strategies" : "Show Mitigation Strategies"}
                    </Button>
                </div>
            </div>
        </div>
    );
}

