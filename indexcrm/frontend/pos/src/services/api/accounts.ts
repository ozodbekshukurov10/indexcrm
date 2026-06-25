import { apiRequest } from "./client";
import { UserAccount } from "./types";

export function getCurrentUser() {
  return apiRequest<UserAccount>("/accounts/me/");
}

export function getMyProfile() {
  return apiRequest<UserAccount["profile"]>("/accounts/me/profile/");
}
