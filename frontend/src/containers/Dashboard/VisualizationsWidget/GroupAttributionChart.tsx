import React, { useEffect, useState } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import type { Campaign } from "../../../types/campaign.ts";
import { Button, DropdownMenu } from "@radix-ui/themes";

interface GroupSimilarity {
    group_name: string;
    cosine: number;
    tfidf: number;
    graph: number;
    is_attributed: boolean;
    group_description?: string;
}

interface GroupSimilarityProps {
    campaign?: Campaign | null;
}

const CampaignGroupSimilarityChart: React.FC<GroupSimilarityProps> = ({ campaign }) => {
    const [data, setData] = useState<GroupSimilarity[]>([]);
    const [attributedGroups, setAttributedGroups] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showDescription, setShowDescription] = useState(false);
    const [simType, setSimType] = useState<"cosine" | "graph">("cosine");

    useEffect(() => {
        if (!campaign) return;

        const fetchSimilarity = async () => {
            setLoading(true);
            setError(null);

            try {
                const res = await fetch(
                    `http://localhost:8000/api/campaigns/${campaign.id}/group-similarity/?type=${simType}`
                );

                if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);

                const json = await res.json();
                console.log(json);

                setData(json.similar_groups || []);
                setAttributedGroups((json.campaign_groups || []));

            } catch (err) {
                console.error(err);
                setError("Failed to load group similarity data.");
            } finally {
                setLoading(false);
            }
        };

        fetchSimilarity();
    }, [campaign, simType]);

    if (loading) return <div className="p-4">Loading...</div>;
    if (error) return <div className="p-4 text-red-600">{error}</div>;
    if (!data.length) return <div className="p-4">No predicted groups found.</div>;

    return (
        <div className="flex flex-col gap-4 h-full p-10">
            <h2 className="section-heading">
                Predicted Groups Similar to <em className="text-blue-700">{campaign?.name}</em>
            </h2>

            {/* Toggle button for explanation */}
            <div className="w-fit">
                <Button
                    variant="outline"
                    color="gray"
                    highContrast
                    size="2"
                    onClick={() => setShowDescription(!showDescription)}
                >
                    About this Visualization
                    <DropdownMenu.TriggerIcon />
                </Button>
            </div>

            {/* Description */}
            {showDescription && (
                <div className="text-sm text-gray-600 text-left mt-3 space-y-2">

                    <p>
                        This chart estimates which threat groups are most similar to the selected campaign.
                        Officially attributed groups (from the database) are marked with a star.
                        The similarity scores are computed automatically based on patterns of techniques, software and tactics.
                    </p>

                    <ul className="list-disc ml-5 space-y-1">

                        <li>
                            <strong>Cosine Similarity</strong> compares the techniques used in the campaign
                            with the techniques used by each group. The score increases when a group and the campaign
                            use many of the same ATT&CK techniques.
                        </li>

                        <li>
                            <strong>TF-IDF Cosine</strong> is similar to cosine similarity but gives more weight
                            to rare techniques. Common techniques like command execution are less important,
                            while uncommon techniques can strongly influence the score.
                        </li>

                        <li>
                            <strong>Graph Similarity</strong> uses the ATT&CK knowledge graph to compare campaigns
                            and groups. It considers connections between campaigns, groups, techniques, software
                            and tactics, not only the techniques themselves. This helps find similarities even when
                            the exact techniques are different.
                        </li>

                    </ul>

                    <p className="mt-2 font-semibold text-gray-700">
                        Goal: Quickly identify which threat groups show similar behaviors to the selected campaign.
                    </p>

                    <p>
                        Note: These similarity scores do not represent confirmed attribution. A group with the highest score is not
                        necessarily the officially attributed one. This visualization is meant to help with analysis
                        and provide clues about potential relationships,
                        but it should not replace expert assessment or be used as an official source.
                    </p>
                </div>
            )}

            {/* Similarity type selector */}
            <div className="mb-4">
                <label className="mr-2 font-semibold">Comparison Method:</label>
                <select
                    value={simType}
                    onChange={(e) => setSimType(e.target.value as "cosine" | "graph")}
                    className="border rounded p-1"
                >
                    <option value="cosine">Technique-based Similarity</option>
                    <option value="graph">Graph-based Similarity</option>
                </select>
            </div>

            <div className="text-sm mb-2">
                {attributedGroups.length > 0 ? (
                    <>
                        <strong>Attributed groups:</strong> {attributedGroups.join(", ")}
                    </>
                ) : (
                    <strong>
                        No groups were yet officially attributed to {campaign?.name}
                    </strong>
                )}
            </div>

            <div className="flex-1">
                <ResponsiveContainer width="100%" height={Math.max(data.length * 50, 400)}>
                    <BarChart data={data} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                            type="number"
                            domain={simType === "graph" ? ['auto', 'auto'] : [0, 1]}
                            tickFormatter={(val) =>
                                simType === "graph" ? val.toFixed(2) : (val * 100).toFixed(0) + "%"
                            }
                        />
                        <YAxis
                            type="category"
                            dataKey="group_name"
                            width={200}
                            interval={0}
                            tick={({ x, y, payload }) => {
                                const groupName = payload.value;
                                const item = data.find(
                                    (d) => d.group_name === groupName
                                );
                                const isAttributed = item?.is_attributed;

                                const display =
                                    (isAttributed ? "★ " : "") +
                                    (groupName.length > 25
                                        ? groupName.slice(0, 25) + "..."
                                        : groupName);

                                return (
                                    <text
                                        x={x}
                                        y={y}
                                        textAnchor="end"
                                        fontSize={13}
                                        fill={isAttributed ? "#e53e3e" : "#1a202c"}
                                        fontWeight={isAttributed ? "bold" : "normal"}
                                    >
                                        {display}
                                    </text>
                                );
                            }}
                        />
                        <Tooltip
                            content={({ active, payload }) => {
                                if (!active || !payload || !payload.length) return null;
                                const barData = payload[0].payload as GroupSimilarity;
                                return (
                                    <div className="bg-white border rounded p-2 shadow-md max-w-xs">
                                        <p className="font-semibold">{barData.group_name}</p>
                                        {simType === "cosine" && (
                                            <>
                                                <p className="text-sm mt-1">Cosine: {(barData.cosine * 100).toFixed(1)}%</p>
                                                <p className="text-sm">TF-IDF: {(barData.tfidf * 100).toFixed(1)}%</p>
                                            </>
                                        )}
                                        {simType === "graph" && (
                                            <p className="text-sm mt-1">Graph similarity: {barData.graph?.toFixed(2)}</p>
                                        )}
                                        {barData.group_description && (
                                            <p className="text-sm text-gray-600 mt-1">{barData.group_description}</p>
                                        )}
                                    </div>
                                );
                            }}
                        />
                        <Legend verticalAlign="top" align="right" />
                        {simType === "cosine" && (
                            <>
                                <Bar dataKey="cosine" name="Cosine Similarity" fill="#d16ba5" />
                                <Bar dataKey="tfidf" name="TF-IDF Cosine" fill="#60a5fa" />
                            </>
                        )}
                        {simType === "graph" && (
                            <Bar dataKey="graph" name="Graph-based Similarity" fill="#805ad5" />
                        )}
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default CampaignGroupSimilarityChart;