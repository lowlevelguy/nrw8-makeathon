#include <stdint.h>
#include <time.h>

#include "stm32f4xx_hal.h"

#include "main.h"
#include "netstack.h"
#include "storage.h"
#include "uart.h"


/* External variables --------------------------------------------------------*/
extern RTC_HandleTypeDef hrtc;


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
 * @return STORAGE_STATUS_OK on success, STORAGE_STATUS_TYPE_OVERFLOW on
 * invalid type, STORAGE_STATUS_INVALID_PARAM if the queue is empty
 */
static storage_status_e free_lane(uint8_t type) {
	if (type >= MAX_TYPE_COUNT) {
		return STORAGE_STATUS_TYPE_OVERFLOW;
	}

	// Pop from type-associated queue
	if (lane_queues[type].size == 0) {
		return STORAGE_STATUS_INVALID_PARAM;
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

	return STORAGE_STATUS_OK;
}

/**
 * @brief Reads the current RTC timestamp.
 *
 * @return seconds since the epoch, -1 on failure
 */
static time_t get_timestamp(void) {
	RTC_TimeTypeDef rtc_time;
	RTC_DateTypeDef rtc_date;

	HAL_RTC_GetTime(&hrtc, &rtc_time, RTC_FORMAT_BIN);
	HAL_RTC_GetDate(&hrtc, &rtc_date, RTC_FORMAT_BIN);

	struct tm timeinfo = {
		.tm_sec = rtc_time.Seconds,
		.tm_min = rtc_time.Minutes,
		.tm_hour = rtc_time.Hours,
		.tm_mday = rtc_date.Date,
		.tm_mon = rtc_date.Month - 1,
		.tm_year = rtc_date.Year + 2000 - 1900,
		.tm_isdst = -1,
	};

	return mktime(&timeinfo);
}

/**
 * @brief Builds and transmits a TX packet over UART.
 *
 * Blocks until the transfer completes.
 *
 * @param type application layer packet type
 * @param params 2-byte application layer parameters
 * @return STORAGE_STATUS_OK on success, STORAGE_STATUS_ERROR if the packet
 * could not be built or transmitted
 */
static storage_status_e send_packet(uint8_t type,
	const uint8_t params[static 2]) {
	packet_t pkt = {0};
	if (netstack_build_packet(0, type, params, &pkt) != NETSTACK_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	if (uart_tx((uint8_t*)&pkt, (uint16_t)sizeof(pkt)) != UART_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	return STORAGE_STATUS_OK;
}

/**
 * @brief Transmits a kernels-NACK carrying the available kernel count.
 *
 * Values above UINT16_MAX report as UINT16_MAX.
 *
 * @param available number of ready kernels currently stored
 * @return STORAGE_STATUS_OK on success, STORAGE_STATUS_ERROR if the packet
 * could not be built or transmitted
 */
static storage_status_e send_nack(uint32_t available) {
	uint16_t reported = (uint16_t)available;
	if (available > UINT16_MAX) {
		reported = UINT16_MAX;
	}
	uint8_t params[] = {
		(uint8_t)(reported >> 8),
		(uint8_t)(reported & UINT8_MAX)
	};

	return send_packet(TX_PACKET_KERNELS_NACK, params);
}

/**
 * @brief Waits for the simulation to acknowledge a box fetch.
 *
 * Receives one packet and checks that it is a box-fetch-done notification.
 *
 * @return STORAGE_STATUS_OK on success, STORAGE_STATUS_ERROR otherwise
 */
static storage_status_e await_fetch_done(void) {
	packet_t rx_pkt = {0};
	if (uart_rx((uint8_t*)&rx_pkt, (uint16_t)sizeof(rx_pkt))
		!= UART_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	uint8_t is_rx = 0;
	uint8_t type = 0;
	uint8_t params[2] = {0};
	if (netstack_breakdown_packet(&rx_pkt, &is_rx, &type, params)
		!= NETSTACK_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	if (is_rx != 1) {
		return STORAGE_STATUS_ERROR;
	}

	if (type != RX_PACKET_BOX_FETCH_DONE) {
		return STORAGE_STATUS_ERROR;
	}

	return STORAGE_STATUS_OK;
}

/**
 * @brief Counts ready kernels along a type FIFO.
 *
 * Walks lanes then boxes in FIFO order and stops at the first box stored
 * for less than MIN_STORAGE_DURATION.
 *
 * @param type type index to walk
 * @param count demand to count towards
 * @param now current timestamp
 * @param n_boxes out: boxes holding the counted kernels
 * @param leftover out: counted kernels above @p count, 0 when short
 * @return counted ready kernels
 */
static uint32_t count_ready(uint8_t type, uint32_t count, uint32_t now,
	uint16_t* n_boxes, uint8_t* leftover) {
	uint32_t available = 0;
	uint16_t boxes = 0;

	for (uint16_t i = 0; i < lane_queues[type].size; i++) {
		uint16_t slot = (lane_queues[type].head_index + i) % LANE_COUNT;
		lane_t* lane = &lanes[lane_queues[type].lane_indices[slot]];
		for (uint16_t j = 0; j < lane->box_count; j++) {
			box_t* box =
				&lane->boxes[(lane->box_head_index + j) % LANE_LENGTH];
			if (now < box->entry_timestamp) {
				goto done;
			}
			if ((now - box->entry_timestamp) < MIN_STORAGE_DURATION) {
				goto done;
			}
			available += box->kernel_count;
			boxes++;
			if (available >= count) {
				goto done;
			}
		}
	}

done:
	*n_boxes = boxes;
	*leftover = 0;
	if (available >= count) {
		// Leftover is smaller than one box, so it fits in a byte
		*leftover = (uint8_t)(available - count);
	}
	return available;
}

/**
 * @brief Emits the counted boxes over UART.
 *
 * Sends one output lane select per box, waiting for a box-fetch-done reply
 * each time. Fully served boxes leave the lane; the last box keeps @p
 * leftover kernels when nonzero.
 *
 * @param type type index being served
 * @param n_boxes number of boxes to emit
 * @param leftover kernels kept in the last box
 * @return STORAGE_STATUS_OK on success, STORAGE_STATUS_ERROR on packet
 * failure
 *
 * @note Stops on the first packet failure; lanes already emptied stay
 * released.
 */
static storage_status_e serve_boxes(uint8_t type, uint16_t n_boxes,
	uint8_t leftover) {
	uint16_t served = 0;
	while (served < n_boxes) {
		// Always serve the head lane; freeing it advances the queue
		uint16_t lane_idx =
			lane_queues[type].lane_indices[lane_queues[type].head_index];
		lane_t* lane = &lanes[lane_idx];
		uint8_t lane_coords[] = {
			(uint8_t)(lane_idx % SHELF_WIDTH),
			(uint8_t)(lane_idx / SHELF_WIDTH)
		};

		while (lane->box_count > 0 && served < n_boxes) {
			uint8_t select_type = TX_PACKET_SELECT_OUTPUT_LANE;
			uint8_t partial = 0;
			if (served + 1 == n_boxes && leftover > 0) {
				select_type = TX_PACKET_SELECT_OUTPUT_LANE_AND_RESTOCK;
				partial = 1;
			}

			if (send_packet(select_type, lane_coords) != STORAGE_STATUS_OK) {
				return STORAGE_STATUS_ERROR;
			}
			if (await_fetch_done() != STORAGE_STATUS_OK) {
				return STORAGE_STATUS_ERROR;
			}

			if (partial != 0) {
				lane->boxes[lane->box_head_index].kernel_count = leftover;
			} else {
				lane->box_head_index =
					(lane->box_head_index + 1) % LANE_LENGTH;
				lane->box_count--;
			}
			served++;
		}

		if (lane->box_count == 0) {
			// Should never fail: the emptied lane is the head
			if (free_lane(type) != STORAGE_STATUS_OK) {
				Error_Handler();
			}
		}
	}

	return STORAGE_STATUS_OK;
}


/* Public functions ----------------------------------------------------------*/
void storage_init(void) {
	for (uint16_t i = 0; i < LANE_COUNT; i++) {
		free_lanes.lane_indices[i] = i;
	}
}

uint8_t store_box(uint8_t type, uint8_t capacity) {
	if (type >= MAX_TYPE_COUNT) {
		return STORAGE_STATUS_TYPE_OVERFLOW;
	}

	int16_t lane_idx = -1;

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

	if (lane_idx < 0) {
		return STORAGE_STATUS_RACK_FULL;
	}

	// Push new box to lane
	time_t ts = get_timestamp();
	if (ts == -1) {
		// Should never be reached
		Error_Handler();
	}

	box_t new_box = {
		.type = type,
		.kernel_count = capacity,
		.entry_timestamp = (uint32_t)ts
	};

	lanes[lane_idx].box_count++;
	uint16_t box_tail_idx =
		(lanes[lane_idx].box_head_index + lanes[lane_idx].box_count - 1)
		% LANE_LENGTH;
	lanes[lane_idx].boxes[box_tail_idx] = new_box;

	// Build UART TX packet and transmit
	packet_t pkt = {0};
	uint8_t lane_coords[] = {
		(uint8_t)(lane_idx % SHELF_WIDTH),
		(uint8_t)(lane_idx / SHELF_WIDTH)
	};

	if (netstack_build_packet(0, TX_PACKET_SELECT_INPUT_LANE, lane_coords, &pkt)
		== NETSTACK_STATUS_OK) {
		if (uart_tx((uint8_t*)&pkt, (uint16_t)sizeof(pkt))
			!= UART_STATUS_OK) {
			lanes[lane_idx].box_count--;
			return STORAGE_STATUS_ERROR;
		}
		return STORAGE_STATUS_OK;
	} else {
		// Should never be reached
		return STORAGE_STATUS_ERROR;
	}
}

storage_status_e fetch_kernels(uint8_t type, uint32_t count) {
	if (type >= MAX_TYPE_COUNT) {
		return STORAGE_STATUS_TYPE_OVERFLOW;
	}

	if (count == 0) {
		return STORAGE_STATUS_INVALID_PARAM;
	}

	// No lanes of this type: report nothing ready
	if (lane_queues[type].size == 0) {
		if (send_nack(0) != STORAGE_STATUS_OK) {
			return STORAGE_STATUS_ERROR;
		}
		return STORAGE_STATUS_INSUFFICIENT;
	}

	time_t ts = get_timestamp();
	if (ts == -1) {
		// Should never be reached
		Error_Handler();
	}
	uint32_t now = (uint32_t)ts;

	// Count ready boxes along the FIFO
	uint16_t n_boxes = 0;
	uint8_t leftover = 0;
	uint32_t available = count_ready(type, count, now, &n_boxes, &leftover);
	if (available < count) {
		if (send_nack(available) != STORAGE_STATUS_OK) {
			return STORAGE_STATUS_ERROR;
		}
		return STORAGE_STATUS_INSUFFICIENT;
	}

	// Tell the dashboard how many boxes follow
	uint8_t ack_boxes = (uint8_t)n_boxes;
	if (n_boxes > UINT8_MAX) {
		ack_boxes = UINT8_MAX;
	}
	uint8_t ack_params[] = {ack_boxes, leftover};
	if (send_packet(TX_PACKET_KERNELS_ACK, ack_params)
		!= STORAGE_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	if (serve_boxes(type, n_boxes, leftover) != STORAGE_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	uint8_t complete_params[] = {0, 0};
	if (send_packet(TX_PACKET_FETCH_COMPLETE, complete_params)
		!= STORAGE_STATUS_OK) {
		return STORAGE_STATUS_ERROR;
	}

	return STORAGE_STATUS_OK;
}
