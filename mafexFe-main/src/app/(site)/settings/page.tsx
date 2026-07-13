"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { LoadingState } from "@/components/shared/LoadingState";
import { PageHeader } from "@/components/shared/PageHeader";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";
import { OTP_CODE_LENGTH } from "@/lib/constants/auth";
import {
  listMyEmailHistory,
  requestEmailChangeOtp,
  updateMe,
  verifyEmailChangeOtp,
} from "@/lib/api/users";
import type { UserEmailHistoryOut } from "@/lib/types/api";
import { formatApiError } from "@/lib/utils/errors";
import { useAuth } from "@/hooks/use-auth";

const nameSchema = z.object({
  full_name: z.string().min(1, "Enter your name").max(255),
});

const emailSchema = z.object({
  new_email: z.string().email("Enter a valid email"),
});

const otpSchema = z.object({
  otp: z
    .string()
    .length(OTP_CODE_LENGTH, `Enter the ${OTP_CODE_LENGTH}-digit code`)
    .regex(/^\d+$/, "Digits only"),
});

function SettingsContent() {
  const { user, refresh } = useAuth();
  const [history, setHistory] = useState<UserEmailHistoryOut[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [emailStep, setEmailStep] = useState<"email" | "otp">("email");
  const [pendingEmail, setPendingEmail] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);

  const nameForm = useForm<z.infer<typeof nameSchema>>({
    resolver: zodResolver(nameSchema),
    defaultValues: { full_name: user?.full_name ?? "" },
  });

  const emailForm = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
    defaultValues: { new_email: "" },
  });

  const otpForm = useForm<z.infer<typeof otpSchema>>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: "" },
  });

  const loadHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      setHistory(await listMyEmailHistory());
    } catch (e) {
      toast.error(formatApiError(e));
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (user) nameForm.reset({ full_name: user.full_name });
  }, [user, nameForm]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  async function onSaveName(values: z.infer<typeof nameSchema>) {
    setSavingName(true);
    try {
      await updateMe({ full_name: values.full_name.trim() });
      await refresh();
      toast.success("Name updated.");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSavingName(false);
    }
  }

  async function onRequestEmail(values: z.infer<typeof emailSchema>) {
    setSavingEmail(true);
    try {
      await requestEmailChangeOtp({ new_email: values.new_email.trim() });
      setPendingEmail(values.new_email.trim());
      setEmailStep("otp");
      toast.success("Check your new email for a verification code.");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSavingEmail(false);
    }
  }

  async function onVerifyEmail(values: z.infer<typeof otpSchema>) {
    setSavingEmail(true);
    try {
      await verifyEmailChangeOtp({ new_email: pendingEmail, otp: values.otp });
      await refresh();
      setEmailStep("email");
      setPendingEmail("");
      emailForm.reset({ new_email: "" });
      otpForm.reset({ otp: "" });
      void loadHistory();
      toast.success("Email updated.");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSavingEmail(false);
    }
  }

  if (!user) return <LoadingState />;

  return (
    <div className="mx-auto max-w-2xl space-y-10 px-4 py-8">
      <PageHeader title="Settings" description="Update your profile and email." />

      <section className="space-y-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">Profile</h2>
        <form onSubmit={nameForm.handleSubmit(onSaveName)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" {...nameForm.register("full_name")} />
          </div>
          <Button type="submit" disabled={savingName}>
            {savingName ? "Saving…" : "Save name"}
          </Button>
        </form>
      </section>

      <section className="space-y-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">Email</h2>
        <p className="text-sm text-muted-foreground">
          Current: <span className="font-medium text-foreground">{user.email}</span>
        </p>
        {emailStep === "email" ? (
          <form onSubmit={emailForm.handleSubmit(onRequestEmail)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new_email">New email</Label>
              <Input id="new_email" type="email" {...emailForm.register("new_email")} />
            </div>
            <Button type="submit" disabled={savingEmail}>
              {savingEmail ? "Sending…" : "Send verification code"}
            </Button>
          </form>
        ) : (
          <form onSubmit={otpForm.handleSubmit(onVerifyEmail)} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Enter the code sent to <span className="font-medium text-foreground">{pendingEmail}</span>
            </p>
            <div className="space-y-2">
              <Label htmlFor="otp">Verification code</Label>
              <Input id="otp" inputMode="numeric" {...otpForm.register("otp")} />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={savingEmail}>
                {savingEmail ? "Verifying…" : "Confirm new email"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEmailStep("email");
                  setPendingEmail("");
                  otpForm.reset();
                }}
              >
                Cancel
              </Button>
            </div>
          </form>
        )}
      </section>

      <section className="space-y-4 rounded-lg border p-6">
        <h2 className="text-lg font-semibold">Previous emails</h2>
        {loadingHistory ? (
          <LoadingState />
        ) : history.length === 0 ? (
          <EmptyState title="No previous emails" description="Past addresses appear here after you change email." />
        ) : (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Changed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((h) => (
                  <TableRow key={h.id}>
                    <TableCell>{h.email}</TableCell>
                    <TableCell className="text-muted-foreground">{h.changed_at.slice(0, 19).replace("T", " ")}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  );
}
