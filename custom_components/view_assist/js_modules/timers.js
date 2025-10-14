// Generate timer cards list to display timers

class TimerCards {
    timerCards(show_all = false) {
        const entity_id = localStorage.getItem("view_assist_sensor");
        const cards = Array();

        // If not timers return empty list
        if (!window.viewassist?.config?.timers) return cards;

        window.viewassist.config?.timers.forEach((timer) => {
            // If not matchin supplied entity id, skip this timer
            if (!show_all && entity_id && timer.entity_id != entity_id) return;

            const name = timer.name ? timer.name : timer.extra_info.sentence;
            const cancelButton = {
                "type": "custom:button-card",
                "name": "Cancel",
                "icon": "mdi:alarm-off",
                "show_name": false,
                "tap_action": {
                    "action": "call-service",
                    "service": "view_assist.cancel_timer",
                    "service_data": {
                        "timer_id": timer.id
                    }
                },
                "styles": {
                    "card": [
                        { "justify-self": "end" },
                        { "align-self": "center" },
                        { "border-radius": "0 10px 10px 0" },
                        { "background-color": "rgba(255, 0, 0, 1)" },
                        { "color": "white" },
                        { "height": "20vh" },
                        { "width": "10vw" },
                    ],
                    "icon": [
                        { "color": "white" }
                    ]
                }
            };

            const timerCard = {
                "type": "custom:button-card",

                "name": name,
                "styles": {
                    "grid": [
                        { "grid-template-areas": "'n time cancel'" },
                        { "grid-template-rows": "1fr" },
                        { "grid-template-columns": "45% 40% 15%" }
                    ],
                    "card": [
                        { "background-color": "rgba(0, 0, 0, 0.7)" },
                        { "border-radius": "3vh" },
                        { "width": "90vw" },
                        { "height": "20vh" },
                        { "padding": "0" },
                    ],
                    "name": [
                        { "color": "white" },
                        { "font-size": "3vw" },
                        { "justify-self": "start" },
                        { "text-align": "left" },
                        { "padding-left": "2vw" },
                    ],
                    "custom_fields": {
                        "time": [
                            { "color": "white" },
                            { "font-size": "5vw" },
                            { "justify-self": "end" },
                            { "padding-right": "3vw" }
                        ],
                        "cancel": [
                            { "justify-self": "end" }
                        ]
                    }
                },
                "custom_fields": {
                    "time": (timer.timer_type == 'interval') ? `<viewassist-countdown expires='${timer.expires}'></viewassist-countdown>` : '',
                    "cancel": {
                        "card": {
                            ...cancelButton
                        }
                    }
                }
            };
            cards.push(timerCard);
        });
        return cards;
    }
}

export const timerCards = new TimerCards();