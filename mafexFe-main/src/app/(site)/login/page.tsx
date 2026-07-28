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
import { PageHeader } from "@/components/shared/PageHeader";
import { useT } from "@/i18n/use-t";
import { loginRequestOtp, loginVerifyOtp } from "@/lib/api/auth";
import { OTP_CODE_LENGTH } from "@/lib/constants/auth";
import { formatApiError } from "@/lib/utils/errors";
import { FIND_ROOM_PATH } from "@/lib/routes";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const t = useT();
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);

  const emailSchema = useMemo(
    () =>
      z.object({
        email: z.string().email(t("auth.invalidEmail")),
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

  const emailForm = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  const otpForm = useForm<z.infer<typeof otpSchema>>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: "" },
  });

  async function onEmail(values: z.infer<typeof emailSchema>) {
    setSending(true);
    try {
      await loginRequestOtp(values.email);
      setEmail(values.email);
      setStep("otp");
      toast.success(t("auth.checkEmailLogin"));
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSending(false);
    }
  }

  async function onOtp(values: z.infer<typeof otpSchema>) {
    setSending(true);
    try {
      await loginVerifyOtp({ email, otp: values.otp });
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
      <PageHeader title={t("auth.loginTitle")} description={t("auth.loginDescription")} />
      {step === "email" ? (
        <form onSubmit={emailForm.handleSubmit(onEmail)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">{t("auth.emailLabel")}</Label>
            <Input id="email" type="email" autoComplete="email" {...emailForm.register("email")} />
            {emailForm.formState.errors.email && (
              <p className="text-xs text-destructive">{emailForm.formState.errors.email.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={sending}>
            {sending ? t("auth.sending") : t("auth.sendCode")}
          </Button>
        </form>
      ) : (
        <form onSubmit={otpForm.handleSubmit(onOtp)} className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {t("auth.codeSentTo")} <span className="font-medium text-foreground">{email}</span>
          </p>
          <div className="space-y-2">
            <Label htmlFor="otp">{t("auth.otpLabel")}</Label>
            <Input
              id="otp"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={OTP_CODE_LENGTH}
              {...otpForm.register("otp")}
            />
            {otpForm.formState.errors.otp && (
              <p className="text-xs text-destructive">{otpForm.formState.errors.otp.message}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="outline" className="flex-1" onClick={() => setStep("email")}>
              {t("common.back")}
            </Button>
            <Button type="submit" className="flex-1" disabled={sending}>
              {sending ? t("auth.verifying") : t("auth.verify")}
            </Button>
          </div>
        </form>
      )}
      <p className="mt-8 text-center text-sm text-muted-foreground">
        {t("auth.needAccount")}{" "}
        <Link href="/signup" className="text-primary underline underline-offset-4">
          {t("common.signUp")}
        </Link>
      </p>
    </div>
  );
}
