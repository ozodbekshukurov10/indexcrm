import { apiRequest } from "./client";
import {
  AIChatResponse,
  AIChatSession,
  AIChatSessionDetail,
  PaginatedResponse,
} from "./types";

export type SendAIMessagePayload = {
  message: string;
  session_id?: string | number | null;
};

export type SendAIFeedbackPayload = {
  message_id: string;
  rating: "good" | "bad";
  comment?: string;
};

export type AIFeedbackResponse = {
  status: "ok";
  message: string;
};

export function sendAIMessage(payload: SendAIMessagePayload) {
  return apiRequest<AIChatResponse>("/ai/chat/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAISessions() {
  return apiRequest<PaginatedResponse<AIChatSession>>("/ai/sessions/");
}

export function getAISessionDetail(id: string) {
  return apiRequest<AIChatSessionDetail>(`/ai/sessions/${id}/`);
}

export function sendAIFeedback(payload: SendAIFeedbackPayload) {
  return apiRequest<AIFeedbackResponse>("/ai/feedback/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
