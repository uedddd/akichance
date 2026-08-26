export type SeatStatus   = 'empty' | 'in_use' | 'reserved';
export type SeatType     = 'desk' | 'conf' | 'free';
export type SeatCapacity = 4 | 6 | 8 | 10 | null;
export type FloorNumber  = 4 | 5 | 6;

export type Seat = {
  id          : number;
  seat_code   : string;
  seat_name   : string;
  floor       : FloorNumber;
  seat_type   : SeatType;
  status      : SeatStatus;
  capacity    : SeatCapacity;
  has_monitor : boolean;
  next_info   : string;
  updated_at  : string;
};

export type TimelineBlock = {
  status : 'in_use' | 'reserved';
  left   : number;
  width  : number;
  label  : string;
};

export type TimelineRow = {
  seat_code   : string;
  seat_name   : string;
  seat_type   : SeatType;
  capacity    : SeatCapacity;
  has_monitor : boolean;
  blocks      : TimelineBlock[];
};

export type FilterState = {
  types   : SeatType[];
  monitor : boolean;
  caps    : SeatCapacity[];
};

export type SummaryCount = {
  total    : number;
  vacant   : number;
  inuse    : number;
  reserved : number;
};

export type ReserveFormInput = {
  seatName  : string;
  userName  : string;
  startTime : string;
  endTime   : string;
};