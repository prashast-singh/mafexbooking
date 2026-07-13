"use client";

import { Fragment, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PurposeText } from "@/components/shared/PurposeText";
import {
  dateRangeLabel,
  groupBookingsBySeries,
  seriesFrequencyLabel,
} from "@/features/admin/admin-bookings-grouping";
import type { PendingBookingOut } from "@/lib/types/api";

type Props = {
  rows: PendingBookingOut[];
  onApprove: (id: number) => void;
  onDeny: (id: number) => void;
  onApproveSeries: (seriesId: number) => void;
  onDenySeries: (seriesId: number) => void;
};

export function AdminBookingRequestsTable({
  rows,
  onApprove,
  onDeny,
  onApproveSeries,
  onDenySeries,
}: Props) {
  const grouped = useMemo(() => groupBookingsBySeries(rows), [rows]);
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
                  <TableCell>{b.room_name}</TableCell>
                  <TableCell>{b.unit_name}</TableCell>
                  <TableCell>{b.booking_date}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                  </TableCell>
                  <TableCell className="max-w-[280px]">
                    <PurposeText purpose={b.purpose} />
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button size="sm" onClick={() => onApprove(b.id)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => onDeny(b.id)}>
                      Deny
                    </Button>
                  </TableCell>
                </TableRow>
              );
            }

            const { seriesId, bookings } = row;
            const head = bookings[0];
            if (!head) return null;
            const isOpen = expanded[seriesId] ?? false;
            const freq = seriesFrequencyLabel(head);

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
                  <TableCell>{head.room_name}</TableCell>
                  <TableCell>{head.unit_name}</TableCell>
                  <TableCell>
                    <div>{dateRangeLabel(bookings)}</div>
                    <div className="text-xs text-muted-foreground">{bookings.length} pending</div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {head.start_time.slice(0, 5)} – {head.end_time.slice(0, 5)}
                  </TableCell>
                  <TableCell className="max-w-[280px]">
                    <PurposeText purpose={head.purpose} />
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button size="sm" onClick={() => onApproveSeries(seriesId)}>
                      Approve all
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => onDenySeries(seriesId)}>
                      Deny all
                    </Button>
                  </TableCell>
                </TableRow>
                {isOpen &&
                  bookings.map((b) => (
                    <TableRow key={`series-${seriesId}-${b.id}`} className="bg-muted/10">
                      <TableCell />
                      <TableCell className="font-mono text-xs pl-6">{b.id}</TableCell>
                      <TableCell className="text-xs text-muted-foreground" colSpan={2}>
                        {freq ? `${freq} · ` : ""}
                        {b.booking_date}
                      </TableCell>
                      <TableCell />
                      <TableCell>{b.booking_date}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                      </TableCell>
                      <TableCell />
                      <TableCell className="text-right space-x-2">
                        <Button size="sm" onClick={() => onApprove(b.id)}>
                          Approve
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => onDeny(b.id)}>
                          Deny
                        </Button>
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
