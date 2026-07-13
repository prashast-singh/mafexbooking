import { apiFetch, setStoredToken } from "@/lib/api/client";
import type {
  LoginRequestOtpBody,
  ResendOtpRequestBody,
  SignupRequestBody,
  TokenResponse,
  UserPublic,
  VerifyOtpRequestBody,
} from "@/lib/types/api";

export async function signupRequest(body: SignupRequestBody) {
  return apiFetch<{ detail: string }>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(body),
    auth: false,
  });
}

export async function verifySignupOtp(body: VerifyOtpRequestBody) {
  const res = await apiFetch<TokenResponse>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify(body),
    auth: false,
  });
  setStoredToken(res.access_token);
  return res;
}

export async function resendOtp(body: ResendOtpRequestBody) {
  return apiFetch<{ detail: string }>("/auth/resend-otp", {
    method: "POST",
    body: JSON.stringify(body),
    auth: false,
  });
}

export async function loginRequestOtp(email: string) {
  const body: LoginRequestOtpBody = { email };
  return apiFetch<{ detail: string }>("/auth/login/request-otp", {
    method: "POST",
    body: JSON.stringify(body),
    auth: false,
  });
}

export async function loginVerifyOtp(body: VerifyOtpRequestBody) {
  const res = await apiFetch<TokenResponse>("/auth/login/verify-otp", {
    method: "POST",
    body: JSON.stringify(body),
    auth: false,
  });
  setStoredToken(res.access_token);
  return res;
}

export async function fetchMe(): Promise<UserPublic> {
  return apiFetch<UserPublic>("/auth/me");
}

export function logoutClient() {
  setStoredToken(null);
}
