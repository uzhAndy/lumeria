import React, {useEffect, useState} from "react";
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDownIcon } from "@radix-ui/react-icons";
import type {Campaign} from "../../../types/campaign.ts";
import type {Faq} from "../../../types/faq.ts";
import { Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {Button} from "@radix-ui/themes";


interface FaqWidgetProps {
    campaign?: Campaign | null
}

const FaqWidget: React.FC<FaqWidgetProps> = ({ campaign }) => {
    const [faqs, setFaqs] = useState<Faq[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    useEffect(() => {
        if (!campaign) return;

        const fetchFaqs = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await fetch(
                    `http://localhost:8000/api/campaigns/${campaign.id}/faqs/`,
                    {
                        method: "GET",
                        headers: { "Content-Type": "application/json" },
                    }
                );
                const data: Faq[] = await res.json();
                setFaqs(data);
                console.log(data);
            }
            finally {
                setLoading(false);
            }
        };

        fetchFaqs().catch((err) => {
            console.error("Unhandled fetchFaqs error:", err);
            setError("Could not fetch FAQ.");
        });
    }, [campaign]);

    if (!campaign) {
        return <p>Select a campaign to see FAQs.</p>;
    }

    if (loading) {
        return <p>Loading FAQs...</p>;
    }

    if (error) {
        return <p className="flex flex-col h-full rounded p-20 text-red-600 font-bold">Error: {error}</p>;
    }

    if (faqs.length === 0) {
        return <p className="flex flex-col h-full rounded p-20 font-bold">No FAQs available for this campaign.</p>;
    }

    return (
        <div className="flex flex-col h-full rounded p-10">
            <h2 className="section-heading">
                FAQs about <em className={"text-blue-700"}>{campaign?.name}</em>
            </h2>

            <Accordion.Root
                type="multiple"
                className="space-y-3"
            >
                {faqs.map((faq, index) => (
                    <Accordion.Item
                        key={faq.id}
                        value={`item-${index}`}
                        className="rounded-lg border"
                    >
                        <Accordion.Header>
                            <Accordion.Trigger className="group flex w-full items-start px-4 py-3 text-left font-medium">
                                {/* optional AI icon */}
                                <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center mt-1">
                                    {faq.is_ai_generated && <Sparkles className="h-5 w-5 text-blue-600" aria-label="AI generated" />}
                                </div>

                                {/* question text */}
                                <div className="flex-1 ml-3">
                                    <span className="break-words">{faq.question}</span>
                                </div>

                                {/* chevron to display answer */}
                                <div className="flex-shrink-0 ml-3 mt-1">
                                    <ChevronDownIcon className="h-4 w-4 transition-transform duration-200 group-data-[state=open]:rotate-180" />
                                </div>
                            </Accordion.Trigger>

                        </Accordion.Header>

                        <Accordion.Content className="
                            overflow-hidden px-4 pb-4 text-sm text-gray-600
                            data-[state=open]:animate-accordion-down
                            data-[state=closed]:animate-accordion-up
                            text-left whitespace-pre-wrap pt-2
                            "
                        >
                            {faq.answer}
                        </Accordion.Content>
                    </Accordion.Item>
                ))}
            </Accordion.Root>
            <div className="flex justify-end p-4">
                <Button
                    size={"3"}
                    onClick={() => navigate(`/faq-management/${campaign.id}`, {
                        state: { campaign }
                    })}
                >
                    View and Edit FAQs
                </Button>
            </div>
        </div>
    );
};

export default FaqWidget;