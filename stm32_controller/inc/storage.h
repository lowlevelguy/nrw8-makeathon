#ifndef STORAGE_H_
#define STORAGE_H_

#ifdef __cplusplus
extern "C" {
#endif


#include <stdint.h>


#define SHELF_WIDTH		15u
#define SHELF_COUNT		26u
#define LANE_LENGTH		10u
#define MAX_TYPE_COUNT	64u
#define LANE_COUNT		(SHELF_WIDTH * SHELF_COUNT)


/* Types ---------------------------------------------------------------------*/
typedef struct {
	uint8_t type, content_count;
	uint32_t entry_timestamp;
} box_t;

typedef struct {
	box_t boxes[LANE_LENGTH];
	uint8_t box_count;
} lane_t;

typedef struct {
	uint16_t lane_indices[LANE_COUNT];
	uint16_t size;
	uint16_t head_index;
} lane_queue_t;


/* Public variables ----------------------------------------------------------*/
extern lane_t lanes[LANE_COUNT];


/* Public functions ----------------------------------------------------------*/
/**
 * @brief Initialises the lane allocator.
 *
 * Seeds the free queue with all lane indices in ascending order. Must be
 * called once before any alloc_lane or free_lane call.
 */
void storage_init(void);

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
int16_t alloc_lane(uint8_t type);

/**
 * @brief Releases the oldest allocated lane of a type to the free queue.
 *
 * Pops the head of the FIFO queue of @p type (the longest-allocated lane) and
 * pushes it onto the free queue.
 *
 * @param type type index of the queue to pop the lane from
 * @return 0 on success, -1 on invalid type, -2 if the queue is empty
 */
int8_t free_lane(uint8_t type);


#ifdef __cplusplus
}
#endif

#endif /* STORAGE_H_ */
