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

interface TacticMetrics {
    tactic: string;
    technique_count: number;
}

interface OperationalAttributionProps {
    campaign?: Campaign | null;
}

const TacticsChart: React.FC<OperationalAttributionProps> = ({ campaign }) => {
    const [data, setData] = useState<TacticMetrics[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showDescription, setShowDescription] = useState(false);

    useEffect(() => {
        if (!campaign) return;

        const fetchTacticData = async () => {
            setLoading(true);
            setError(null);

            try {
                const res = await fetch(
                    `http://localhost:8000/api/campaigns/${campaign.id}/tactic-technique-count/`,
                    { method: "GET" }
                );

                if (!res.ok) {
                    throw new Error(`HTTP error! Status: ${res.status}`);
                }

                const json = await res.json();
                setData(json.data || [])
            } catch (err) {
                console.error(err);
                setError("Failed to load tactic technique counts.");
            } finally {
                setLoading(false);
            }
        };

        fetchTacticData();
    }, [campaign]);

    if (loading) return <div className="p-4">Loading...</div>;
    if (error) return <div className="p-4 text-red-600">{error}</div>;
    if (!data.length) return <div className="p-4">No tactics found.</div>;

    return (
        <div className="flex flex-col gap-4 h-full p-10">
            <h2 className="section-heading">
                Identify Most Targeted Tactics for <em className="text-blue-700">{campaign?.name}</em>
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

            {/* Description and Goal */}
            {showDescription && (
                <div className="text-sm text-gray-600 text-left mt-2">
                    <p>
                        This chart shows all tactics used in the selected campaign and counts how many techniques were applied to each tactic.
                    </p>
                    <ul className="list-disc ml-5 mt-1 space-y-1">
                        <li>
                            <strong>Tactic Name</strong>: Each tactic from the campaign is displayed on the y-axis. If no domain is specified, the tactic belongs to the Enterprise domain.
                        </li>
                        <li>
                            <strong>Technique Count</strong>: The number of techniques applied to each tactic. This indicates which tactics are most frequently targeted.
                        </li>
                    </ul>
                    <p className="mt-2 font-semibold text-gray-700">
                        Goal: See which tactics were used in this campaign and which ones were targeted the most.
                    </p>
                </div>
            )}

            {/* Chart */}
            <div className="flex-1">
                <ResponsiveContainer width="100%" height={Math.max(data.length * 50, 400)}>
                    <BarChart data={data} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" allowDecimals={false}/>
                        <YAxis
                            type="category"
                            dataKey="tactic"
                            width={200}
                            interval={0}
                            tick={({ x, y, payload }) => {
                                const transformed = payload.value
                                const display = transformed.length > 29 ? transformed.slice(0, 25) + ".." : transformed;
                                return (
                                    <text x={x} y={y} textAnchor="end" fontSize={13}>
                                        {display}
                                    </text>
                                );
                            }}
                        />
                        <Tooltip
                            content={({ active, payload }) => {
                                if (!active || !payload || !payload.length) return null;
                                const barData = payload[0].payload as TacticMetrics & { description?: string };

                                return (
                                    <div className="bg-white border rounded p-2 shadow-md max-w-xs">
                                        <p className="font-semibold">{barData.tactic}</p>
                                        <p className="text-sm mt-1">Number of Used Techniques: {barData.technique_count}</p>
                                        {barData.description && (
                                            <p className="text-sm text-gray-600 mt-1">
                                                <strong>Tactic Description:<br /></strong>
                                                {barData.description}
                                            </p>
                                        )}
                                    </div>
                                );
                            }}
                        />
                        <Legend verticalAlign="top" align="right" />
                        <Bar dataKey="technique_count" fill="#3182ce" name="Technique Count" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default TacticsChart;