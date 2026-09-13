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


#ifdef __cplusplus
}
#endif

#endif /* STORAGE_H_ */
