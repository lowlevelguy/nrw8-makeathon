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
#define MIN_STORAGE_DURATION	1000u


/* Types ---------------------------------------------------------------------*/
typedef enum {
	STORAGE_STATUS_OK,
	STORAGE_STATUS_TYPE_OVERFLOW,
	STORAGE_STATUS_RACK_FULL,
	STORAGE_STATUS_INVALID_PARAM,
	STORAGE_STATUS_INSUFFICIENT,
	STORAGE_STATUS_ERROR,
} storage_status_e;

typedef struct {
	uint8_t type, kernel_count;
	uint32_t entry_timestamp;
} box_t;

typedef struct {
	box_t boxes[LANE_LENGTH];
	uint8_t box_count;
	uint8_t box_head_index;
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
 * @brief Initialises the storage module.
 */
void storage_init(void);

/**
 * @brief Stores a new box in the rack.
 *
 * Appends the box to the currently allocated lane of @p type, allocating a
 * new lane if none is allocated yet or the latest one is full.
 *
 * @param type type index of the box contents
 * @param capacity kernel capacity of the box
 * @return STORAGE_STATUS_OK on success, STORAGE_STATUS_TYPE_OVERFLOW if @p
 * type is invalid, STORAGE_STATUS_RACK_FULL if no free lanes remain
 */
uint8_t store_box(uint8_t type, uint8_t capacity);

/**
 * @brief Serves a production demand for kernels of a given type.
 *
 * Counts the kernels held in ready boxes (stored for at least
 * MIN_STORAGE_DURATION) along the FIFO of lanes allocated to @p type. If
 * the demand can be served, a kernels-ACK packet is transmitted right away,
 * followed by one output lane select per box; the simulation must
 * acknowledge every box with a box-fetch-done packet before the next box is
 * sent. A box holding more kernels than the demand still needs is only
 * partially served through a select-output-lane-and-restock packet, and its
 * leftover kernels stay stored in place. If the demand cannot be served, a
 * kernels-NACK packet carrying the available kernel count is transmitted
 * and no box is released.
 *
 * @param type type index of the requested kernels
 * @param count number of kernels requested
 * @return STORAGE_STATUS_OK if the demand was served,
 * STORAGE_STATUS_TYPE_OVERFLOW if @p type is invalid,
 * STORAGE_STATUS_INVALID_PARAM if @p count is zero,
 * STORAGE_STATUS_INSUFFICIENT if fewer ready kernels are stored than
 * requested (a kernels-NACK is transmitted), STORAGE_STATUS_ERROR if a
 * packet could not be built, transmitted or acknowledged
 *
 * @note The kernels-ACK packet reports the number of boxes served in a
 * single byte; a demand spanning more than 255 boxes is reported as 255.
 */
storage_status_e fetch_kernels(uint8_t type, uint32_t count);

#ifdef __cplusplus
}
#endif

#endif /* STORAGE_H_ */
