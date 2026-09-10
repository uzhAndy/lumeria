import {useEffect, useRef, useState} from "react";
import {Button} from "@radix-ui/themes";
import AttackExplanation from "./AttackExplanation.tsx";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { PaperPlaneIcon } from '@radix-ui/react-icons'

import type {Campaign} from "../../../types/campaign.ts";
import type {ReferenceTag} from "../../../types/reference.ts";
import {CornerDownRight} from "lucide-react";

interface Message {
    id: number;
    sender: "bot" | "user";
    text: string;
}

interface ChatBotWidgetProps {
    campaign?: Campaign | null
}

const ChatBotWidget: React.FC<ChatBotWidgetProps> = ({campaign}) => {
    const [typedText, setTypedText] = useState("");
    const [reference, setReference] = useState<ReferenceTag | null>(null);
    const [loading, setLoading] = useState(false);
    const initialMessage = (campaign?: Campaign | null): Message => ({
        id: 0,
        sender: "bot" as const,
        text: `Hello, I’m your cybersecurity assistant. I will guide you through an attack example from your selected campaign${campaign ? ` ${campaign.name}` : ""}. 
        If you have any questions about the campaign or related cybersecurity terms, please don’t hesitate to ask.`
    });

    const [messages, setMessages] = useState<Message[]>([initialMessage(campaign)]);

    // reset whenever campaign changes
    useEffect(() => {
        const reset = () => {
            setMessages([initialMessage(campaign)]);
        };
        reset();
    }, [campaign]);


    // used to always scroll to the newest message
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({behavior: "smooth", block: "end"});
    }, [messages]);

    // Send message handler
    const handleSend = async () => {
        if (!typedText.trim()) return;

        const userMessage: Message = {
            id: Date.now(),
            sender: "user",
            text: reference
                ? reference.label.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) + ": " + typedText.trim()
                : typedText.trim(),
        };
        setMessages((prev) => [...prev, userMessage]);
        const payload = {
            message: typedText.trim(),
            reference,
        };
        setTypedText("");
        setReference(null);
        setLoading(true);

        try {
            console.log(payload);
            const res = await fetch(`http://localhost:8000/api/campaigns/${campaign?.id}/chatbot/`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            console.log(data)

            const botMessage: Message = {
                id: Date.now() + 1,
                sender: "bot",
                text: data,
            };

            setMessages((prev) => [...prev, botMessage]);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const triggerTacticExplanation = async (tacticName: string) => {
        try {
            console.log(tacticName)
            const res = await fetch(
                `http://localhost:8000/api/campaigns/${campaign?.id}/chatbot/attack-story/`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        current_tactic: tacticName.toString()
                    }),
                }
            );
            const data = await res.json();
            console.log(data);

            const botMessage: Message = {
                id: Date.now(),
                sender: "bot",
                text: data.response,
            };

            setMessages((prev) => [...prev, botMessage]);
        } catch (err) {
            console.error("Error fetching tactic explanation:", err);
        }
    };

    const insertReference = (ref: ReferenceTag) => {
        setReference(ref);
    };

    return (
        <div className="flex w-full h-full overflow-hidden">
            {/* Chat area */}
            <div className="flex flex-col w-2/5 border-r border-gray-300 p-4">
                <div className="flex flex-col flex-1 overflow-y-auto space-y-2">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`p-2 rounded-md max-w-[70%] ${
                                msg.sender === "bot"
                                    ? "bg-gray-200 text-gray-900 self-start text-left"
                                    : "bg-blue-500 text-white self-end text-left"
                            }`}
                        >
                            <div className="prose max-w-none">
                                <ReactMarkdown rehypePlugins={[rehypeSanitize]}>
                                    {msg.text}
                                </ReactMarkdown>
                            </div>
                        </div>
                    ))}
                    {/* Message processing indicator */}
                    {loading && (
                        <div className="p-2 rounded-md max-w-[70%] bg-gray-200 text-gray-900 self-start">
                            <span className="text-xs text-gray-600">
                                Analyzing MITRE ATT&CK data
                            </span>
                            <div className="flex space-x-1">
                                <span className="animate-bounce">•</span>
                                <span className="animate-bounce [animation-delay:0.2s]">•</span>
                                <span className="animate-bounce [animation-delay:0.4s]">•</span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef}/>
                </div>

                {/* Input area */}
                <div className="mt-0.5 flex flex-col gap-0.5  border border-gray-200">
                    {/* Reference */}
                    {reference && (
                        <div className="items-center ">
                            <span
                                className="flex items-center justify-between text-gray-600 text-xs font-medium px-2 py-1">
                                <div className="flex gap-4">
                                {/* Arrow */}
                                    <CornerDownRight
                                        size={15}
                                        strokeWidth={2}
                                        className="text-gray-800"
                                        aria-hidden
                                    />
                                    {reference.label.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                                </div>
                                <button
                                    onClick={() => setReference(null)}
                                    className="text-gray-800 hover:text-gray-700">
                                    ×
                                </button>
                            </span>
                        </div>
                    )}
                    <div className="flex items-center pr-5 pl-4 pt-2 pb-2">
                        <input
                            className="flex-1 bg-transparent border-0 outline-none focus:outline-none focus:ring-0"
                            placeholder="Type a message..."
                            value={typedText}
                            disabled={loading}
                            onChange={(e) => setTypedText(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") handleSend();
                            }}
                        />
                        <Button variant={"ghost"} size={"4"} onClick={handleSend} disabled={loading}>
                            {loading ? "..." : <PaperPlaneIcon />}
                        </Button>
                    </div>
                </div>
            </div>

            {/* Display of techniques */}
            <div className="w-3/5 p-4 pt-7 bg-gray-50 dark:bg-gray-900 flex flex-col h-full overflow-y-auto">
                <h2 className="section-heading"><em className={"text-blue-700"}>{campaign?.name}</em> — Threat Brief</h2>
                <p className="text-gray-700 dark:text-gray-300 text-left text-sm">
                    Click through the tactics across the different Unified Kill Chain phases to explore a typical attack progression for the campaign.
                    As you do so, the chatbot will explain what an attack in this campaign could look like.
                    This is only a representative scenario. In reality, tactics rarely occur in a strictly linear order and the exact timeline of an attack is often unknown.
                </p>
                <div className="flex-1 flex flex-col">
                    <AttackExplanation
                        campaign={campaign}
                        onTacticShown={triggerTacticExplanation}
                        onInsertReference={insertReference}
                    />
                </div>
            </div>
        </div>
    );
};

export default ChatBotWidget;

