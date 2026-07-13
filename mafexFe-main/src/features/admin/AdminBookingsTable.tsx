"use client";

import { Fragment, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PurposeText } from "@/components/shared/PurposeText";
import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  dateRangeLabel,
  groupAdminBookings,
  seriesFrequencyLabel,
  statusSummary,
} from "@/features/admin/admin-bookings-grouping";
import type { AdminBookingListItem } from "@/lib/types/api";

export type CancelTarget =
  | { type: "single"; bookingId: number }
  | { type: "series"; seriesId: number; fromDate?: string };

function canModifyBooking(status: string) {
  return status === "confirmed" || status === "pending";
}

type Props = {
  rows: AdminBookingListItem[];
  roomNames?: Record<number, string>;
  onCancel: (target: CancelTarget) => void;
  onEdit?: (booking: AdminBookingListItem) => void;
};

function roomLabel(booking: AdminBookingListItem, roomNames?: Record<number, string>) {
  return booking.room_name || roomNames?.[booking.room_id] || String(booking.room_id);
}

function canCancelBooking(status: string) {
  return status === "confirmed" || status === "pending";
}

export function AdminBookingsTable({ rows, roomNames, onCancel, onEdit }: Props) {
  const grouped = useMemo(() => groupAdminBookings(rows), [rows]);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  function toggleSeries(seriesId: number) {
    setExpanded((prev) => ({ ...prev, [seriesId]: !prev[seriesId] }));
  }

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <TableHead>ID</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Room</TableHead>
            <TableHead>Unit</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Time</TableHead>
            <TableHead>Purpose</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Series</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {grouped.map((row) => {
            if (row.kind === "single") {
              const b = row.booking;
              return (
                <TableRow key={`single-${b.id}`}>
                  <TableCell />
                  <TableCell className="font-mono text-xs">{b.id}</TableCell>
                  <TableCell>
                    <div className="text-sm">{b.user_full_name}</div>
                    <div className="text-xs text-muted-foreground">{b.user_email}</div>
                  </TableCell>
                  <TableCell>{roomLabel(b, roomNames)}</TableCell>
                  <TableCell>{b.unit_name}</TableCell>
                  <TableCell>{b.booking_date}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                  </TableCell>
                  <TableCell className="max-w-[240px]">
                    <PurposeText purpose={b.purpose} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge value={b.status} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">—</TableCell>
                  <TableCell className="text-right space-x-2">
                    {canModifyBooking(b.status) && onEdit && (
                      <Button variant="outline" size="sm" onClick={() => onEdit(b)}>
                        Edit
                      </Button>
                    )}
                    {canCancelBooking(b.status) && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onCancel({ type: "single", bookingId: b.id })}
                      >
                        Cancel
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            }

            const { seriesId, bookings } = row;
            const head = bookings[0];
            if (!head) return null;
            const isOpen = expanded[seriesId] ?? false;
            const freq = seriesFrequencyLabel(head);
            const summary = statusSummary(bookings);
            const singleStatus = bookings.every((b) => b.status === bookings[0]?.status);
            const cancellable = bookings.some((b) => canCancelBooking(b.status));
            const mixedUnits = bookings.some((b) => b.unit_name !== head.unit_name);

            return (
              <Fragment key={`series-${seriesId}`}>
                <TableRow className="bg-muted/20">
                  <TableCell>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => toggleSeries(seriesId)}
                      aria-label={isOpen ? "Collapse series" : "Expand series"}
                    >
                      {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </Button>
                  </TableCell>
                  <TableCell className="font-mono text-xs">#{seriesId}</TableCell>
                  <TableCell>
                    <div className="text-sm">{head.user_full_name}</div>
                    <div className="text-xs text-muted-foreground">{head.user_email}</div>
                  </TableCell>
                  <TableCell>{roomLabel(head, roomNames)}</TableCell>
                  <TableCell>
                    {head.unit_name}
                    {mixedUnits && (
                      <div className="text-xs text-muted-foreground">some dates differ</div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div>{dateRangeLabel(bookings)}</div>
                    <div className="text-xs text-muted-foreground">{bookings.length} booking(s)</div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {head.start_time.slice(0, 5)} – {head.end_time.slice(0, 5)}
                  </TableCell>
                  <TableCell className="max-w-[240px]">
                    <PurposeText purpose={head.purpose} />
                  </TableCell>
                  <TableCell>
                    {singleStatus && head ? (
                      <StatusBadge value={head.status} />
                    ) : (
                      <span className="text-xs text-muted-foreground">{summary}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    #{seriesId}
                    {freq ? ` · ${freq}` : ""}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    {cancellable && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onCancel({ type: "series", seriesId })}
                      >
                        Cancel all future
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
                {isOpen &&
                  bookings.map((b) => (
                    <TableRow key={`series-${seriesId}-${b.id}`} className="bg-muted/10">
                      <TableCell />
                      <TableCell className="font-mono text-xs pl-6">{b.id}</TableCell>
                      <TableCell className="text-xs text-muted-foreground" colSpan={2}>
                        Occurrence {b.occurrence_index ?? "—"}
                      </TableCell>
                      <TableCell className={b.unit_name !== head.unit_name ? "font-medium" : undefined}>
                        {b.unit_name}
                      </TableCell>
                      <TableCell>{b.booking_date}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                      </TableCell>
                      <TableCell />
                      <TableCell>
                        <StatusBadge value={b.status} />
                      </TableCell>
                      <TableCell />
                      <TableCell className="text-right space-x-2">
                        {canModifyBooking(b.status) && onEdit && (
                          <Button variant="outline" size="sm" onClick={() => onEdit(b)}>
                            Edit
                          </Button>
                        )}
                        {canCancelBooking(b.status) && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onCancel({ type: "single", bookingId: b.id })}
                            >
                              Cancel
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                onCancel({
                                  type: "series",
                                  seriesId,
                                  fromDate: b.booking_date,
                                })
                              }
                            >
                              Cancel from date
                            </Button>
                          </>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
