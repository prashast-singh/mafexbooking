"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/shared/PageHeader";
import { useT } from "@/i18n/use-t";
import { signupRequest, verifySignupOtp } from "@/lib/api/auth";
import { OTP_CODE_LENGTH } from "@/lib/constants/auth";
import { formatApiError } from "@/lib/utils/errors";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

export default function SignupPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const t = useT();
  const [step, setStep] = useState<"details" | "otp">("details");
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);

  const signupSchema = useMemo(
    () =>
      z.object({
        email: z.string().email(t("auth.invalidEmail")),
        full_name: z.string().min(1, t("auth.enterName")),
        signup_intent: z
          .string()
          .trim()
          .min(1, t("auth.intentRequired"))
          .max(2000, t("auth.intentTooLong")),
      }),
    [t],
  );

  const otpSchema = useMemo(
    () =>
      z.object({
        otp: z
          .string()
          .length(OTP_CODE_LENGTH, t("auth.otpLength", { n: OTP_CODE_LENGTH }))
          .regex(/^\d+$/, t("auth.digitsOnly")),
      }),
    [t],
  );

  const detailsForm = useForm<z.infer<typeof signupSchema>>({
    resolver: zodResolver(signupSchema),
    defaultValues: { email: "", full_name: "", signup_intent: "" },
  });

  const otpForm = useForm<z.infer<typeof otpSchema>>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: "" },
  });

  async function onDetails(values: z.infer<typeof signupSchema>) {
    setSending(true);
    try {
      await signupRequest({
        email: values.email,
        full_name: values.full_name,
        signup_intent: values.signup_intent.trim(),
      });
      setEmail(values.email);
      setStep("otp");
      toast.success(t("auth.checkEmailSignup"));
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
      <PageHeader title={t("auth.signupTitle")} description={t("auth.signupDescription")} />
      {step === "details" ? (
        <form onSubmit={detailsForm.handleSubmit(onDetails)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="full_name">{t("auth.fullName")}</Label>
            <Input id="full_name" autoComplete="name" {...detailsForm.register("full_name")} />
            {detailsForm.formState.errors.full_name && (
              <p className="text-xs text-destructive">
                {detailsForm.formState.errors.full_name.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">{t("auth.emailLabel")}</Label>
            <Input id="email" type="email" autoComplete="email" {...detailsForm.register("email")} />
            {detailsForm.formState.errors.email && (
              <p className="text-xs text-destructive">{detailsForm.formState.errors.email.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="signup_intent">{t("auth.signupIntentLabel")}</Label>
            <Textarea
              id="signup_intent"
              rows={4}
              placeholder={t("auth.signupIntentPlaceholder")}
              {...detailsForm.register("signup_intent")}
            />
            {detailsForm.formState.errors.signup_intent && (
              <p className="text-xs text-destructive">
                {detailsForm.formState.errors.signup_intent.message}
              </p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={sending}>
            {sending ? t("auth.sending") : t("auth.continue")}
          </Button>
        </form>
      ) : (
        <form onSubmit={otpForm.handleSubmit(onOtp)} className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t("auth.enterCodeSentTo")} <span className="font-medium text-foreground">{email}</span>
          </p>
          <div className="space-y-2">
            <Label htmlFor="otp">{t("auth.otpLabel")}</Label>
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
              {t("common.back")}
            </Button>
            <Button type="submit" className="flex-1" disabled={sending}>
              {sending ? t("auth.verifying") : t("auth.createAccount")}
            </Button>
          </div>
        </form>
      )}
      <p className="mt-8 text-center text-sm text-muted-foreground">
        {t("auth.haveAccount")}{" "}
        <Link href="/login" className="text-primary underline underline-offset-4">
          {t("common.logIn")}
        </Link>
      </p>
    </div>
  );
}
