#include <stddef.h>
#include "netstack.h"

typedef struct {
	packet_type_e type;
	uint8_t (*callback)(void*);
} packet_handler_t;

static uint8_t box_metadata_handler(void* payload) {
	save_box();
	position = solve_position();
	uart_tx(position);
}

static uint8_t kernels_query_handler(void* payload) {

}

packet_handler_t handlers[] = {
	{ PACKET_TYPE_RX_BOX_METADATA_READING, box_metadata_handler },
	{ PACKET_TYPE_RX_KERNELS_QUERY, kernels_query_handler },
};


netstack_status_e netstack_handle(packet_t* pkt) {
	if (pkt == NULL) {
		return NETSTACK_STATUS_NULL_ERROR;
	}

	for (int i = 0; i < PACKET_TYPE_RX_COUNT; i++) {
		if (pkt->link_header.type == handlers[i].type) {
			return handlers[i].callback(pkt);
		}
	}
}