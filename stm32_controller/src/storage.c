#include "storage.h"


/* Private variables ---------------------------------------------------------*/
static lane_queue_t free_lanes = {
	.size = LANE_COUNT,
	.head_index = 0
};

static lane_queue_t lane_queues[MAX_TYPE_COUNT] = {0};


/* Public variables ----------------------------------------------------------*/
lane_t lanes[LANE_COUNT];


/* Public functions ----------------------------------------------------------*/
void storage_init(void) {
	for (uint16_t i = 0; i < LANE_COUNT; i++) {
		free_lanes.lane_indices[i] = i;
	}
}

int16_t alloc_lane(uint8_t type) {
	if (type >= MAX_TYPE_COUNT) {
		return -1;
	}

	// Pop free lane
	if (free_lanes.size == 0) {
		return -2;
	}

	uint16_t lane_idx = free_lanes.lane_indices[free_lanes.head_index];
	free_lanes.head_index++;
	free_lanes.head_index %= LANE_COUNT;
	free_lanes.size--;

	/* Push to type-associated queue.
	 *
	 * Note: no bounds checking is needed for indexing into lane_queues[type],
	 * since a necessary condition for it to be full is for free_lanes to be
	 * empty, which is already checked for.
	 */
	lane_queues[type].size++;
	uint16_t tail_idx =
		(lane_queues[type].head_index + lane_queues[type].size - 1)
		% LANE_COUNT;
	lane_queues[type].lane_indices[tail_idx] = lane_idx;

	return lane_idx;
}

int8_t free_lane(uint8_t type) {
	if (type >= MAX_TYPE_COUNT) {
		return -1;
	}

	// Pop from type-associated queue
	if (lane_queues[type].size == 0) {
		return -2;
	}

	uint16_t lane_idx =
		lane_queues[type].lane_indices[lane_queues[type].head_index];
	lane_queues[type].head_index++;
	lane_queues[type].head_index %= LANE_COUNT;
	lane_queues[type].size--;

	// Push free lane
	free_lanes.size++;
	uint16_t tail_idx =
		(free_lanes.head_index + free_lanes.size - 1) % LANE_COUNT;
	free_lanes.lane_indices[tail_idx] = lane_idx;

	return 0;
}
