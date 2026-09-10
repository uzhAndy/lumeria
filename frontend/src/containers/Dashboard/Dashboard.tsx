// inspired by https://medium.com/@mohdkhan.mk99/interactive-dashboards-recharts-react-grid-layout-a12952bbd0e0
import {useEffect, useState} from "react";
import Responsive from "react-grid-layout";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
import ChatBotWidget from "./ChatbotWidget/ChatbotWidget";
import SummaryWidget from "./SummaryWidget/SummaryWidget";
import {Flex, IconButton} from "@radix-ui/themes";
import {Cross1Icon} from "@radix-ui/react-icons";
import {CheckboxGroup} from "@radix-ui/themes";
import CampaignDropdown from "./CampaignDropdown.tsx";
import FaqWidget from "./FaqWidget/FaqWidget.tsx";
import GroupAttributionChart from "./VisualizationsWidget/GroupAttributionChart";
import PlatformsChart from "./VisualizationsWidget/PlatformsChart";
import TacticsChart from "./VisualizationsWidget/TacticsChart";
import TechniquesChart from "./VisualizationsWidget/TechniquesChart";
import type {Campaign} from "../../types/campaign.ts";
import {format} from "date-fns";
import { useLocation } from "react-router-dom";
import { DropdownMenu, Button } from "@radix-ui/themes";

type WidgetType =
    | "ChatBot"
    | "SummaryCard"
    | "FaqCard"
    | "GroupAttributionChart"
    | "PlatformsChart"
    | "TacticsChart"
    | "TechniquesChart";

interface Widget {
    i: string;
    x: number;
    y: number;
    w: number;
    h: number;
    type: WidgetType;
}

const initialWidgets: Widget[] = [
    {i: "0", x: 0, y: 0, w: 12, h: 5, type: "ChatBot"},
    {i: "1", x: 0, y: 1, w: 6, h: 4, type: "SummaryCard"},
    {i: "2", x: 6, y: 1, w: 6, h: 4, type: "FaqCard"},
    {i: "3", x: 0, y: 2, w: 7, h: 5, type: "TechniquesChart"},
    {i: "4", x: 7, y: 2, w: 5, h: 5, type: "PlatformsChart"},
    {i: "5", x: 0, y: 3, w: 5, h: 5, type: "TacticsChart"},
    {i: "6", x: 5, y: 3, w: 7, h: 5, type: "GroupAttributionChart"},
];

const Dashboard = () => {
    const [widgets, setWidgets] = useState<Widget[]>(initialWidgets);
    const widgetExists = (type: WidgetType) =>
        widgets.some(w => w.type === type);
    const location = useLocation();
    const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(() => {
        const stored = sessionStorage.getItem("selectedCampaign");
        return location.state?.selectedCampaign ?? (stored ? JSON.parse(stored) : null);
    });

    useEffect(() => {
        if (selectedCampaign) {
            sessionStorage.setItem("selectedCampaign", JSON.stringify(selectedCampaign));
        }
    }, [selectedCampaign]);

    const removeWidgetByType = (type: WidgetType) => {
        setWidgets(prev => prev.filter(w => w.type !== type));
    };

    const selectedWidgetTypes: WidgetType[] = widgets.map(w => w.type);

    const handleRemove = (id: string) => {
        setWidgets((prev) => prev.filter((w) => w.i !== id));
    };

    const sizeMap: Record<WidgetType, { w: number; h: number }> = {
        ChatBot: {w: 12, h: 5},
        SummaryCard: {w: 6, h: 4},
        FaqCard: {w: 6, h: 4},
        GroupAttributionChart: {w: 6, h: 4},
        PlatformsChart: {w: 6, h: 4},
        TacticsChart: {w: 6, h: 4},
        TechniquesChart: {w: 8, h: 4},
    };

    const handleAddWidget = (type: WidgetType) => {
        const newWidget: Widget = {
            i: Date.now().toString(), // ensures widget has a unique id
            x: 0, // places the widget in the leftmost column
            y: Infinity, // places the widget at the lowest available row
            w: sizeMap[type].w,
            h: sizeMap[type].h,
            type,
        };
        setWidgets((prev) => [...prev, newWidget]);
    };

    return (
        <div>
            <div className="flex flex-row gap-25 pt-5 pl-8 pb-2.5">
                <div>
                    {selectedCampaign ? (
                        <div className="flex flex-col items-start">
                            <h2 className="text-2xl font-semibold"><em
                                className={"text-blue-700"}>{selectedCampaign.name}</em></h2>
                            <p className="text-sm text-gray-500">
                                Last seen:{" "}
                                {selectedCampaign
                                    ? format(new Date(selectedCampaign.last_seen), "PPP")
                                    : "—"}{" "}
                            </p>
                        </div>
                    ) : (
                        <div className="text-xl font-semibold">Select a campaign to get started</div>
                    )}
                </div>
                <div className="flex flex-wrap gap-15">
                    {/* Campaign Dropdown beside buttons */}
                    <div className="flex flex-col items-start gap-1">
                        <label className="font-semibold">
                            {selectedCampaign
                                ? `Select another campaign:`
                                : "Select a campaign to analyze:"}
                        </label>
                        <CampaignDropdown
                            selectedCampaign={selectedCampaign}
                            setSelectedCampaign={setSelectedCampaign}
                        />
                    </div>
                    <div className="flex flex-col items-start gap-1">
                        <label className="font-semibold"> Select widgets to display: </label>
                        <CheckboxGroup.Root
                            size="3"
                            value={selectedWidgetTypes}
                            onValueChange={(values) => {
                                const next = values as WidgetType[];

                                // Add newly checked widgets
                                next.forEach(type => {
                                    if (!widgetExists(type)) {
                                        handleAddWidget(type);
                                    }
                                });

                                // Remove unchecked widgets
                                selectedWidgetTypes.forEach(type => {
                                    if (!next.includes(type)) {
                                        removeWidgetByType(type);
                                    }
                                });
                            }}
                        >
                            <Flex gap="5" align="center">

                                {/* Main widgets */}
                                <Flex gap="3">
                                    <CheckboxGroup.Item value="ChatBot">
                                        Threat Brief
                                    </CheckboxGroup.Item>
                                    <CheckboxGroup.Item value="SummaryCard">
                                        Executive Summary
                                    </CheckboxGroup.Item>
                                    <CheckboxGroup.Item value="FaqCard">
                                        FAQs
                                    </CheckboxGroup.Item>
                                </Flex>

                                {/* Visualization section */}
                                <DropdownMenu.Root
                                >
                                    <DropdownMenu.Trigger>
                                        <Button variant="outline" color="gray" highContrast size={"3"}>
                                            Visualizations
                                            <DropdownMenu.TriggerIcon />
                                        </Button>
                                    </DropdownMenu.Trigger>

                                    <DropdownMenu.Content>
                                        <CheckboxGroup.Root
                                            value={selectedWidgetTypes}
                                            onValueChange={(values) => {
                                                const next = values as WidgetType[];

                                                next.forEach(type => {
                                                    if (!widgetExists(type)) handleAddWidget(type);
                                                });

                                                selectedWidgetTypes.forEach(type => {
                                                    if (!next.includes(type)) removeWidgetByType(type);
                                                });
                                            }}
                                        >
                                            <Flex direction="column" gap="3" p="2">
                                                <CheckboxGroup.Item value="GroupAttributionChart">
                                                    Group Attribution
                                                </CheckboxGroup.Item>
                                                <CheckboxGroup.Item value="PlatformsChart">
                                                    Platforms
                                                </CheckboxGroup.Item>
                                                <CheckboxGroup.Item value="TacticsChart">
                                                    Tactics
                                                </CheckboxGroup.Item>
                                                <CheckboxGroup.Item value="TechniquesChart">
                                                    Techniques
                                                </CheckboxGroup.Item>
                                            </Flex>
                                        </CheckboxGroup.Root>
                                    </DropdownMenu.Content>
                                </DropdownMenu.Root>

                            </Flex>
                        </CheckboxGroup.Root>
                    </div>
                </div>
            </div>

            <Responsive
                className="layouts"
                width={window.innerWidth - 15}
            >
                {widgets.map((widget) => (
                    <div
                        key={widget.i}
                        data-grid={{
                            i: widget.i,
                            x: widget.x,
                            y: widget.y,
                            w: widget.w,
                            h: widget.h,
                            minW: 2,
                            minH: 2,
                            isDraggable: true,
                            isResizable: true,
                        }}
                        className="bg-white rounded shadow-md overflow-hidden relative"
                    >
                        <div className="relative h-full overflow-auto">
                            <IconButton
                                color="red"
                                variant="ghost"
                                highContrast
                                style={{
                                    position: "absolute",
                                    top: "4px",
                                    right: "4px",
                                    zIndex: 10,
                                    padding: "10px"
                                }} // used style because button didn't recognize tailwindcss
                                onClick={() => handleRemove(widget.i)}
                            >
                                <Cross1Icon className="text-gray-900 scale-110"/>
                            </IconButton>
                            {widget.type === "ChatBot" && <ChatBotWidget campaign={selectedCampaign}/>}
                            {widget.type === "SummaryCard" && <SummaryWidget campaign={selectedCampaign}/>}
                            {widget.type === "FaqCard" && <FaqWidget campaign={selectedCampaign}/>}
                            {widget.type === "GroupAttributionChart" && (<GroupAttributionChart campaign={selectedCampaign} />)}
                            {widget.type === "PlatformsChart" && (<PlatformsChart campaign={selectedCampaign} />)}
                            {widget.type === "TacticsChart" && (<TacticsChart campaign={selectedCampaign} />)}
                            {widget.type === "TechniquesChart" && (<TechniquesChart campaign={selectedCampaign} />)}
                        </div>
                    </div>
                ))}
            </Responsive>
        </div>
    );
};

export default Dashboard;
