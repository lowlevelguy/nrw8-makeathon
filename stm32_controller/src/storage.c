#include "storage.h"

#include "netstack.h"
#include "uart.h"


/* Private variables ---------------------------------------------------------*/
static lane_queue_t free_lanes = {
	.size = LANE_COUNT,
	.head_index = 0
};

static lane_queue_t lane_queues[MAX_TYPE_COUNT] = {0};


/* Public variables ----------------------------------------------------------*/
lane_t lanes[LANE_COUNT];


/* Private functions ---------------------------------------------------------*/
/**
 * @brief Allocates a free lane to a type.
 *
 * Pops the oldest free lane from the free queue and appends it to the FIFO
 * queue of @p type.
 *
 * @param type type index of the queue to append the lane to
 * @return lane index in [0, LANE_COUNT) on success, -1 on invalid type, -2 if
 * no free lanes remain
 */
static int16_t alloc_lane(uint8_t type) {
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

/**
 * @brief Releases the oldest allocated lane of a type to the free queue.
 *
 * Pops the head of the FIFO queue of @p type (the longest-allocated lane) and
 * pushes it onto the free queue.
 *
 * @param type type index of the queue to pop the lane from
 * @return 0 on success, -1 on invalid type, -2 if the queue is empty
 */
static int8_t free_lane(uint8_t type) {
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

/* Public functions ----------------------------------------------------------*/
void storage_init(void) {
	for (uint16_t i = 0; i < LANE_COUNT; i++) {
		free_lanes.lane_indices[i] = i;
	}
}

int8_t store_box(uint8_t type) {
	if (type >= MAX_TYPE_COUNT) {
		return -1;
	}

	uint16_t lane_idx;

	// If no lane has been allocated previously, allocate one
	if (lane_queues[type].size == 0) {
		lane_idx = alloc_lane(type);
	} else {
		uint16_t latest_lane_idx =
			(lane_queues[type].head_index + lane_queues[type].size - 1)
			% LANE_COUNT;
		latest_lane_idx = lane_queues[type].lane_indices[latest_lane_idx];

		// If the latest lane is full, allocate a new lane.
		if (lanes[latest_lane_idx].box_count == LANE_LENGTH) {
			lane_idx = alloc_lane(type);
		} else {
			// Otherwise use the latest lane
			lane_idx = latest_lane_idx;
		}
	}

	// Build UART TX packet and transmit
	packet_t pkt;
	uint8_t lane_coords[] = {
		lane_idx % LANE_COUNT,
		lane_idx / LANE_COUNT
	};

	if (netstack_build_packet(0, TX_PACKET_SELECT_INPUT_LANE, lane_coords, &pkt)
		== NETSTACK_STATUS_OK ) {
		uart_tx((uint8_t*)&pkt, sizeof(pkt));
	} else {
		// Should never be reached
		return NETSTACK_STATUS_ERROR;
	}
}