import type { Seat, TimelineRow, FloorNumber } from '@/types/seat';

const makeDesks = (floor: FloorNumber): Seat[] => {
  const configs: Array<{
    num: number; cap: number; monitor: boolean; status: Seat['status']
  }> = [
    { num:  1, cap: 4, monitor: false, status: 'empty'    },
    { num:  2, cap: 8, monitor: false, status: 'in_use'   },
    { num:  3, cap: 8, monitor: true,  status: 'empty'    },
    { num:  4, cap: 4, monitor: false, status: 'reserved' },
    { num:  5, cap: 6, monitor: false, status: 'empty'    },
    { num:  6, cap: 4, monitor: false, status: 'in_use'   },
    { num:  7, cap: 4, monitor: false, status: 'empty'    },
    { num:  8, cap: 8, monitor: true,  status: 'reserved' },
    { num:  9, cap: 6, monitor: false, status: 'empty'    },
    { num: 10, cap: 8, monitor: false, status: 'in_use'   },
    { num: 11, cap: 4, monitor: false, status: 'empty'    },
    { num: 12, cap: 4, monitor: false, status: 'empty'    },
  ];

  if (floor === 6) {
    configs[0].status = 'in_use';
    configs[2].status = 'reserved';
    configs[5].status = 'in_use';
    configs[7].status = 'in_use';
    configs[9].status = 'reserved';
  }

  return configs.map((c, i) => ({
    id         : floor * 100 + i + 1,
    seat_code  : `DESK-${floor}-${c.num}`,
    seat_name  : `${floor}-1-${c.num}`,
    floor,
    seat_type  : 'desk' as const,
    status     : c.status,
    capacity   : c.cap as Seat['capacity'],
    has_monitor: c.monitor,
    next_info  : '',
    updated_at : new Date().toISOString(),
  }));
};

const makeConfs = (floor: FloorNumber): Seat[] => {
  const statuses: Seat['status'][] =
    floor === 4 ? ['empty',  'in_use',  'reserved', 'empty',    'reserved', 'in_use'  ] :
    floor === 5 ? ['in_use', 'empty',   'reserved', 'empty',    'in_use',   'reserved'] :
                  ['empty',  'in_use',  'empty',    'reserved', 'empty',    'in_use'  ];

  return statuses.map((status, i) => ({
    id         : floor * 1000 + i + 1,
    seat_code  : `CONF-${floor}-${i + 1}`,
    seat_name  : `会議室0${floor}0${i + 1}`,
    floor,
    seat_type  : 'conf' as const,
    status,
    capacity   : 10 as Seat['capacity'],
    has_monitor: false,
    next_info  : '',
    updated_at : new Date().toISOString(),
  }));
};

const makeFrees = (floor: FloorNumber): Seat[] => {
  const offset = floor === 4 ? 0 : floor === 5 ? 5 : 10;
  const statuses: Seat['status'][] =
    floor === 4 ? ['empty', 'in_use', 'empty',    'empty', 'in_use'  ] :
    floor === 5 ? ['empty', 'empty',  'in_use',   'empty', 'empty'   ] :
                  ['empty', 'in_use', 'empty',    'empty', 'reserved'];

  return statuses.map((status, i) => ({
    id         : floor * 10000 + i + 1,
    seat_code  : `FREE-${offset + i + 1}`,
    seat_name  : `フリー${offset + i + 1}`,
    floor,
    seat_type  : 'free' as const,
    status,
    capacity   : null,
    has_monitor: false,
    next_info  : '',
    updated_at : new Date().toISOString(),
  }));
};

export const DUMMY_SEATS: Record<FloorNumber, Seat[]> = {
  4: [...makeDesks(4), ...makeConfs(4), ...makeFrees(4)],
  5: [...makeDesks(5), ...makeConfs(5), ...makeFrees(5)],
  6: [...makeDesks(6), ...makeConfs(6), ...makeFrees(6)],
};

export const DUMMY_TIMELINE: Record<FloorNumber, TimelineRow[]> = {
  4: [
    { seat_code:'DESK-4-1',  seat_name:'4-1-1（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-4-2',  seat_name:'4-1-2（8名）',   seat_type:'desk', capacity:8,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:16.7, label:'使用中' }] },
    { seat_code:'DESK-4-3',  seat_name:'4-1-3（8名）🖥️', seat_type:'desk', capacity:8,  has_monitor:true,  blocks:[] },
    { seat_code:'DESK-4-4',  seat_name:'4-1-4（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[{ status:'reserved', left:33.3, width:22.2, label:'予約中' }] },
    { seat_code:'DESK-4-5',  seat_name:'4-1-5（6名）',   seat_type:'desk', capacity:6,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-4-6',  seat_name:'4-1-6（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:44.4, label:'使用中' }] },
    { seat_code:'DESK-4-7',  seat_name:'4-1-7（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-4-8',  seat_name:'4-1-8（8名）🖥️', seat_type:'desk', capacity:8,  has_monitor:true,  blocks:[{ status:'reserved', left:11.1, width:33.3, label:'予約中' }] },
    { seat_code:'DESK-4-9',  seat_name:'4-1-9（6名）',   seat_type:'desk', capacity:6,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-4-10', seat_name:'4-1-10（8名）',  seat_type:'desk', capacity:8,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:27.8, label:'使用中' }] },
    { seat_code:'DESK-4-11', seat_name:'4-1-11（4名）',  seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-4-12', seat_name:'4-1-12（4名）',  seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'CONF-4-1',  seat_name:'会議室0401', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-4-2',  seat_name:'会議室0402', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:33.3, label:'使用中' }] },
    { seat_code:'CONF-4-3',  seat_name:'会議室0403', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'reserved', left:22.2, width:11.1, label:'予約中' }] },
    { seat_code:'CONF-4-4',  seat_name:'会議室0404', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-4-5',  seat_name:'会議室0405', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'reserved', left:44.4, width:22.2, label:'予約中' }] },
    { seat_code:'CONF-4-6',  seat_name:'会議室0406', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:22.2, label:'使用中' }] },
    { seat_code:'FREE-1',    seat_name:'フリー1',   seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-2',    seat_name:'フリー2',   seat_type:'free', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:22.2, label:'使用中' }] },
    { seat_code:'FREE-3',    seat_name:'フリー3',   seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-4',    seat_name:'フリー4',   seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-5',    seat_name:'フリー5',   seat_type:'free', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:11.1, width:16.7, label:'使用中' }] },
  ],
  5: [
    { seat_code:'DESK-5-1',  seat_name:'5-1-1（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-5-2',  seat_name:'5-1-2（8名）',   seat_type:'desk', capacity:8,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:22.2, label:'使用中' }] },
    { seat_code:'DESK-5-3',  seat_name:'5-1-3（8名）🖥️', seat_type:'desk', capacity:8,  has_monitor:true,  blocks:[{ status:'reserved', left:11.1, width:22.2, label:'予約中' }] },
    { seat_code:'DESK-5-4',  seat_name:'5-1-4（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-5-5',  seat_name:'5-1-5（6名）',   seat_type:'desk', capacity:6,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:11.1, label:'使用中' }] },
    { seat_code:'DESK-5-6',  seat_name:'5-1-6（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-5-7',  seat_name:'5-1-7（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[{ status:'reserved', left:44.4, width:22.2, label:'予約中' }] },
    { seat_code:'DESK-5-8',  seat_name:'5-1-8（8名）🖥️', seat_type:'desk', capacity:8,  has_monitor:true,  blocks:[] },
    { seat_code:'DESK-5-9',  seat_name:'5-1-9（6名）',   seat_type:'desk', capacity:6,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-5-10', seat_name:'5-1-10（8名）',  seat_type:'desk', capacity:8,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:27.8, label:'使用中' }] },
    { seat_code:'DESK-5-11', seat_name:'5-1-11（4名）',  seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-5-12', seat_name:'5-1-12（4名）',  seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'CONF-5-1',  seat_name:'会議室0501', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:55.6, label:'使用中' }] },
    { seat_code:'CONF-5-2',  seat_name:'会議室0502', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-5-3',  seat_name:'会議室0503', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'reserved', left:11.1, width:22.2, label:'予約中' }] },
    { seat_code:'CONF-5-4',  seat_name:'会議室0504', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-5-5',  seat_name:'会議室0505', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:33.3, label:'使用中' }] },
    { seat_code:'CONF-5-6',  seat_name:'会議室0506', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'reserved', left:22.2, width:22.2, label:'予約中' }] },
    { seat_code:'FREE-6',    seat_name:'フリー6',   seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-7',    seat_name:'フリー7',   seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-8',    seat_name:'フリー8',   seat_type:'free', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:22.2, label:'使用中' }] },
    { seat_code:'FREE-9',    seat_name:'フリー9',   seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-10',   seat_name:'フリー10',  seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
  ],
  6: [
    { seat_code:'DESK-6-1',  seat_name:'6-1-1（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:27.8, label:'使用中' }] },
    { seat_code:'DESK-6-2',  seat_name:'6-1-2（8名）',   seat_type:'desk', capacity:8,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-6-3',  seat_name:'6-1-3（8名）🖥️', seat_type:'desk', capacity:8,  has_monitor:true,  blocks:[{ status:'reserved', left:22.2, width:11.1, label:'予約中' }] },
    { seat_code:'DESK-6-4',  seat_name:'6-1-4（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-6-5',  seat_name:'6-1-5（6名）',   seat_type:'desk', capacity:6,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-6-6',  seat_name:'6-1-6（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:44.4, label:'使用中' }] },
    { seat_code:'DESK-6-7',  seat_name:'6-1-7（4名）',   seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-6-8',  seat_name:'6-1-8（8名）🖥️', seat_type:'desk', capacity:8,  has_monitor:true,  blocks:[{ status:'in_use',   left:0,    width:33.3, label:'使用中' }] },
    { seat_code:'DESK-6-9',  seat_name:'6-1-9（6名）',   seat_type:'desk', capacity:6,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-6-10', seat_name:'6-1-10（8名）',  seat_type:'desk', capacity:8,  has_monitor:false, blocks:[{ status:'reserved', left:11.1, width:33.3, label:'予約中' }] },
    { seat_code:'DESK-6-11', seat_name:'6-1-11（4名）',  seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'DESK-6-12', seat_name:'6-1-12（4名）',  seat_type:'desk', capacity:4,  has_monitor:false, blocks:[] },
    { seat_code:'CONF-6-1',  seat_name:'会議室0601', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-6-2',  seat_name:'会議室0602', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:22.2, label:'使用中' }] },
    { seat_code:'CONF-6-3',  seat_name:'会議室0603', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-6-4',  seat_name:'会議室0604', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'reserved', left:11.1, width:22.2, label:'予約中' }] },
    { seat_code:'CONF-6-5',  seat_name:'会議室0605', seat_type:'conf', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'CONF-6-6',  seat_name:'会議室0606', seat_type:'conf', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:44.4, label:'使用中' }] },
    { seat_code:'FREE-11',   seat_name:'フリー11',  seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-12',   seat_name:'フリー12',  seat_type:'free', capacity:null, has_monitor:false, blocks:[{ status:'in_use',   left:0,    width:16.7, label:'使用中' }] },
    { seat_code:'FREE-13',   seat_name:'フリー13',  seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-14',   seat_name:'フリー14',  seat_type:'free', capacity:null, has_monitor:false, blocks:[] },
    { seat_code:'FREE-15',   seat_name:'フリー15',  seat_type:'free', capacity:null, has_monitor:false, blocks:[{ status:'reserved', left:22.2, width:22.2, label:'予約中' }] },
  ],
};