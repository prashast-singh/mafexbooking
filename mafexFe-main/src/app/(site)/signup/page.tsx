"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader } from "@/components/shared/PageHeader";
import { signupRequest, verifySignupOtp } from "@/lib/api/auth";
import { OTP_CODE_LENGTH } from "@/lib/constants/auth";
import { formatApiError } from "@/lib/utils/errors";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

const signupSchema = z.object({
  email: z.string().email("Enter a valid email"),
  full_name: z.string().min(1, "Enter your name"),
});

const otpSchema = z.object({
  otp: z
    .string()
    .length(OTP_CODE_LENGTH, `Enter the ${OTP_CODE_LENGTH}-digit code from your email`)
    .regex(/^\d+$/, "Digits only"),
});

export default function SignupPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [step, setStep] = useState<"details" | "otp">("details");
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);

  const detailsForm = useForm<z.infer<typeof signupSchema>>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", full_name: "" },
  });

  const otpForm = useForm<z.infer<typeof otpSchema>>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: "" },
  });

  async function onDetails(values: z.infer<typeof signupSchema>) {
    setSending(true);
    try {
      await signupRequest({ email: values.email, full_name: values.full_name });
      setEmail(values.email);
      setStep("otp");
      toast.success("Check your email to verify your account.");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSending(false);
    }
  }

  async function onOtp(values: z.infer<typeof otpSchema>) {
    setSending(true);
    try {
      await verifySignupOtp({ email, otp: values.otp });
      await refresh();
      const { fetchMe } = await import("@/lib/api/auth");
      const me = await fetchMe();
      if (me.approval_status === "pending") router.replace("/awaiting-approval");
      else router.replace(FIND_ROOM_PATH);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <PageHeader title="Sign up" description="Create your account with email verification." />
      {step === "details" ? (
        <form onSubmit={detailsForm.handleSubmit(onDetails)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" autoComplete="name" {...detailsForm.register("full_name")} />
            {detailsForm.formState.errors.full_name && (
              <p className="text-xs text-destructive">
                {detailsForm.formState.errors.full_name.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" {...detailsForm.register("email")} />
            {detailsForm.formState.errors.email && (
              <p className="text-xs text-destructive">{detailsForm.formState.errors.email.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={sending}>
            {sending ? "Sending…" : "Continue"}
          </Button>
        </form>
      ) : (
        <form onSubmit={otpForm.handleSubmit(onOtp)} className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Enter the code we sent to <span className="font-medium text-foreground">{email}</span>
          </p>
          <div className="space-y-2">
            <Label htmlFor="otp">Verification code</Label>
            <Input
              id="otp"
              inputMode="numeric"
              maxLength={OTP_CODE_LENGTH}
              {...otpForm.register("otp")}
            />
            {otpForm.formState.errors.otp && (
              <p className="text-xs text-destructive">{otpForm.formState.errors.otp.message}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" className="flex-1" onClick={() => setStep("details")}>
              Back
            </Button>
            <Button type="submit" className="flex-1" disabled={sending}>
              {sending ? "Verifying…" : "Create account"}
            </Button>
          </div>
        </form>
      )}
      <p className="mt-8 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-primary underline underline-offset-4">
          Log in
        </Link>
      </p>
    </div>
  );
}
