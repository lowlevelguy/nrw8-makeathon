#ifndef STORAGE_H_
#define STORAGE_H_

#include <stdint.h>

typedef struct {
	uint8_t type, content_count;
	uint32_t entry_timestamp;
} box_data_t;



#endif /* STORAGE_H_ */