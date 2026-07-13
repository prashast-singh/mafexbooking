/**
 * Mirrors backend Pydantic models under `app/schemas/` and public room/availability DTOs.
 * Date/time fields are JSON-serialized strings from FastAPI (ISO-8601 dates, HH:MM[:SS] times).
 */

// --- Auth (`app/schemas/auth.py`) ---

export type SignupRequestBody = {
  email: string;
  full_name: string;
};

export type VerifyOtpRequestBody = {
  email: string;
  otp: string;
};

export type ResendOtpRequestBody = {
  email: string;
  /** `"signup"` | `"login"` */
  purpose: "signup" | "login";
};

export type LoginRequestOtpBody = {
  email: string;
};

// --- User (`app/schemas/user.py`) ---

export type UserMeUpdateBody = {
  full_name?: string | null;
};

export type EmailChangeRequestBody = {
  new_email: string;
};

export type EmailChangeVerifyBody = {
  new_email: string;
  otp: string;
};

export type UserEmailHistoryOut = {
  id: number;
  email: string;
  changed_at: string;
};

export type ManagedRoomBrief = {
  id: number;
  name: string;
};

export type UserPublic = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  user_type: string;
  email_verified: boolean;
  approval_status: string;
  is_active: boolean;
  created_at: string;
  approved_at: string | null;
  managed_room_ids: number[];
};

export type TokenResponse = {
  access_token: string;
  /** Default from API: `"bearer"` */
  token_type: string;
};

// --- Amenities (`app/schemas/amenity.py`) ---

export type AmenityBrief = {
  id: number;
  name: string;
  icon: string | null;
};

export type AmenityOut = {
  id: number;
  name: string;
  icon: string | null;
  created_at: string;
};

export type AmenityCreateBody = {
  name: string;
  icon?: string | null;
};

export type AmenityUpdateBody = {
  name?: string | null;
  icon?: string | null;
};

// --- Room browse / public (`app/schemas/room_frontend.py`) ---

export type RoomImageBrief = {
  id: number;
  file_url: string;
  sort_order: number;
};

export type BookableUnitPublic = {
  id: number;
  name: string;
  type: string;
  booking_mode: "direct" | "request";
  capacity: number;
  is_active: boolean;
  parent_unit_id: number | null;
};

export type RoomBrowseItem = {
  id: number;
  name: string;
  description: string | null;
  location: string | null;
  capacity: number;
  booking_mode: string;
  is_active: boolean;
  thumbnail_url: string | null;
  amenities: AmenityBrief[];
  images: RoomImageBrief[];
};

export type RoomBrowsePage = {
  items: RoomBrowseItem[];
  total: number;
  page: number;
  limit: number;
};

export type RoomDetailPublic = {
  id: number;
  name: string;
  description: string | null;
  location: string | null;
  capacity: number;
  booking_mode: string;
  availability_window_start: string;
  availability_window_end: string;
  is_active: boolean;
  thumbnail_url: string | null;
  amenities: AmenityBrief[];
  images: RoomImageBrief[];
  bookable_units: BookableUnitPublic[];
};

export type SlotUnitAvailability = {
  unit_id: number;
  unit_name: string;
  unit_type: string;
  available: boolean;
  reason: string | null;
};

export type SlotAvailabilityRow = {
  start_time: string;
  end_time: string;
  units: SlotUnitAvailability[];
};

export type RoomAvailabilityGrid = {
  room_id: number;
  room_name: string;
  /** `YYYY-MM-DD` */
  date: string;
  slot_minutes: number;
  availability_window_start: string;
  availability_window_end: string;
  slots: SlotAvailabilityRow[];
};

export type AvailabilitySearchResponse = {
  /** `YYYY-MM-DD` */
  date: string;
  slot_minutes: number;
  rooms: RoomAvailabilityGrid[];
};

// --- Room admin (`app/schemas/room.py`) ---

export type BookingMode =
  | "full_room_only"
  | "tables_only"
  | "hybrid"
  | "sections_only";

export type BookableUnitType = "full_room" | "half_room" | "section" | "table";

export type RoomCreateBody = {
  name: string;
  description?: string | null;
  location?: string | null;
  capacity?: number;
  booking_mode: BookingMode;
  availability_window_start?: string;
  availability_window_end?: string;
  is_active?: boolean;
  amenity_ids?: number[] | null;
};

export type RoomUpdateBody = {
  name?: string | null;
  description?: string | null;
  location?: string | null;
  capacity?: number | null;
  booking_mode?: BookingMode | null;
  availability_window_start?: string | null;
  availability_window_end?: string | null;
  is_active?: boolean | null;
  amenity_ids?: number[] | null;
};

export type RoomAmenityAttachBody = {
  amenity_id: number;
};

export type BookableUnitCreateBody = {
  parent_unit_id?: number | null;
  name: string;
  type: BookableUnitType;
  booking_mode?: "direct" | "request";
  capacity?: number;
  is_active?: boolean;
};

export type BookableUnitUpdateBody = {
  parent_unit_id?: number | null;
  name?: string | null;
  type?: BookableUnitType | null;
  booking_mode?: "direct" | "request" | null;
  capacity?: number | null;
  is_active?: boolean | null;
};

export type RoomAdminOut = {
  id: number;
  name: string;
  description: string | null;
  location: string | null;
  capacity: number;
  booking_mode: string;
  availability_window_start: string;
  availability_window_end: string;
  is_active: boolean;
  created_at: string;
  amenities: AmenityOut[];
};

export type RoomImageOut = {
  id: number;
  room_id: number;
  file_url: string;
  sort_order: number;
  created_at: string;
};

export type BookableUnitOut = {
  id: number;
  room_id: number;
  parent_unit_id: number | null;
  name: string;
  type: string;
  booking_mode: "direct" | "request";
  capacity: number;
  is_active: boolean;
};

export type UnitConflictCreateBody = {
  conflict_with_unit_id: number;
};

export type UnitConflictListItem = {
  conflict_unit_id: number;
  relation: "outgoing" | "incoming";
  row_id: number;
};

export type UnitConflictCreateResponse = {
  id: number;
  unit_id: number;
  conflict_with_unit_id: number;
};

// --- Booking (`app/schemas/booking.py`) ---

export type BookingCreateBody = {
  room_id: number;
  unit_id: number;
  /** `YYYY-MM-DD` */
  booking_date: string;
  start_time: string;
  end_time: string;
  purpose?: string | null;
};

export type BookingCancelBody = {
  reason?: string | null;
};

export type BookingOut = {
  id: number;
  user_id: number;
  room_id: number;
  unit_id: number;
  booking_date: string;
  start_time: string;
  end_time: string;
  start_at: string;
  end_at: string;
  purpose: string | null;
  status: string;
  series_id?: number | null;
  occurrence_index?: number | null;
  decided_by_id?: number | null;
  decided_at?: string | null;
  decision_reason?: string | null;
  cancelled_by_id: number | null;
  cancellation_reason: string | null;
  created_at: string;
};

export type PendingBookingOut = BookingOut & {
  room_name: string;
  unit_name: string;
  user_full_name: string;
  user_email: string;
};

export type BookingOutWithRoom = BookingOut & {
  room_name: string;
  room_location: string | null;
};

export type PaginatedBookings = {
  items: BookingOutWithRoom[];
  total: number;
  skip: number;
  limit: number;
};

// --- Booking series (`app/schemas/booking_series.py`) ---

export type BookingSeriesFrequency = "weekly" | "monthly";

export type BookingSeriesCreateBody = {
  room_id: number;
  unit_id: number;
  booking_date: string;
  start_time: string;
  end_time: string;
  purpose?: string | null;
  frequency: BookingSeriesFrequency;
  interval: number;
  end_date?: string | null;
  max_occurrences?: number | null;
};

export type SeriesSkippedItem = {
  date: string;
  reason: string;
};

export type BookingSeriesPreviewOut = {
  total_candidates: number;
  bookable: string[];
  skipped: SeriesSkippedItem[];
};

export type BookingSeriesOut = {
  id: number;
  user_id: number;
  room_id: number;
  unit_id: number;
  start_time: string;
  end_time: string;
  frequency: string;
  interval: number;
  weekday: number;
  series_start_date: string;
  end_date: string | null;
  max_occurrences: number | null;
  purpose: string | null;
  created_at: string;
  created_count: number;
  skipped_count: number;
  bookings: BookingOut[];
  skipped: SeriesSkippedItem[];
};

export type BookingSeriesCancelScope = "all_future" | "from_date";

export type BookingSeriesCancelBody = {
  scope: BookingSeriesCancelScope;
  from_date?: string | null;
  reason?: string | null;
};

export type BookingSeriesCancelOut = {
  cancelled_count: number;
  cancelled_booking_ids: number[];
};

export type AdminBookingListItem = {
  id: number;
  user_id: number;
  user_email: string;
  user_full_name: string;
  room_id: number;
  room_name: string;
  unit_id: number;
  unit_name: string;
  booking_date: string;
  start_time: string;
  end_time: string;
  status: string;
  purpose: string | null;
  series_id?: number | null;
  occurrence_index?: number | null;
  series_frequency?: string | null;
  series_interval?: number | null;
};

export type AdminBookingDetailOut = AdminBookingListItem & {
  room_location: string | null;
  cancellation_reason: string | null;
  created_at: string;
};

// --- Admin (`app/schemas/admin.py`) ---

export type AdminUserOut = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  user_type: string;
  email_verified: boolean;
  approval_status: string;
  is_active: boolean;
  created_at: string;
  approved_at: string | null;
  approved_by_id: number | null;
};

export type AdminRoleUpdateBody = {
  role: "user" | "admin";
};

export type AdminDashboardSummary = {
  pending_approvals: number;
  rooms_total: number;
  bookings_today: number;
  users_total: number;
};

export type InternalDomainOut = {
  id: number;
  domain: string;
  is_active: boolean;
  created_at: string;
};

export type InternalDomainCreateBody = {
  domain: string;
};

export type BookingPolicyOut = {
  id: number;
  slot_minutes: number;
  max_booking_hours_per_day: number;
  max_advance_days: number;
  cancellation_cutoff_minutes: number;
  created_at: string;
  updated_at: string;
};

export type BookingPolicyUpdateBody = {
  slot_minutes?: number | null;
  max_booking_hours_per_day?: number | null;
  max_advance_days?: number | null;
  cancellation_cutoff_minutes?: number | null;
};

export type ApiErrorDetail =
  | string
  | { code?: string; message?: string }
  | Array<{ loc: unknown[]; msg: string; type: string }>;
