#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <assert.h>

#define TEMP_LOW_LIMIT 20    // Heater turns ON if temp < 20°C
#define TEMP_HIGH_LIMIT 300  // Heater turns OFF if temp > 300°C
#define PRESS_LOW_LIMIT 100  // Valve closes if pressure < 100 bar
#define PRESS_HIGH_LIMIT 500 // Valve opens if pressure > 500 bar

float temperature = 0.0;  // Global variable for temperature
float pressure = 0.0;     // Global variable for pressure
bool heater_status = false;  // Heater ON/OFF
bool valve_position = false;  // Valve OPEN/CLOSE

// Simulated ADC functions (Replace with real ADC reads)
float read_temperature_adc() {
    return (rand() % TEMP_HIGH_LIMIT) + 1;  // Simulate temp between 1°C - 300°C
}

float read_pressure_adc() {
    return (rand() % PRESS_HIGH_LIMIT) + 50;  // Simulate pressure between 50 - 500 bar
}

// Simulated DAC function (Replace with real DAC control)
void set_valve_position(bool position) {
    valve_position = position;
    printf("[DAC] Valve set to %s\n", position ? "OPEN" : "CLOSED");
}

// Simulated Heater Control (GPIO)
void set_heater(bool state) {
    heater_status = state;
    printf("[DAC] Heater %s\n", state ? "ON" : "OFF");
}

// Temperature Control Process (T Process)
void *temperature_process(void *arg) {
    while (1) {
        temperature = read_temperature_adc();        
        printf("[T Process] Temperature: %.2f°C\n", temperature);

        if (temperature < TEMP_LOW_LIMIT)
            set_heater(true);
        else if (temperature > TEMP_HIGH_LIMIT) 
            set_heater(false);

        // A T process reads the measured values from a temperature sensor and 
        // turns the heating system on if the temperature is below 20°C and 
        // turns off the heating system if the temperature is above 300°C.
        if (temperature < TEMP_LOW_LIMIT)
          assert(heater_status == true && "Heater should be ON when temperature < 20°C");
        else if (temperature > TEMP_HIGH_LIMIT)
          assert(heater_status == false && "Heater should be OFF when temperature > 300°C");
        sleep(1);
    }
    return NULL;
}

// Pressure Control Process (P Process)
void *pressure_process(void *arg) {
    while (1) {
        pressure = read_pressure_adc();
        printf("[P Process] Pressure: %.2f bar\n", pressure);
        if (pressure > PRESS_HIGH_LIMIT)
            set_valve_position(true);  // Fully open
        else if (pressure < PRESS_LOW_LIMIT)
            set_valve_position(false);  // Fully closed
        // Process P regulates pressure with a sensor opening the pump/valve 
        // when the pressure value is above 500bar and closing the pump/valve 
        // when the pressure value is below 100bar.
        if (pressure > PRESS_HIGH_LIMIT)
          assert(valve_position == true && "Valve should be fully OPEN when pressure > 500 bar");
        else if (pressure < PRESS_LOW_LIMIT)
          assert(valve_position == false && "Valve should be fully CLOSED when pressure < 100 bar");
        sleep(1);
    }
    return NULL;
}

// LCD Display Process (S Process)
void *display_process(void *arg) {
    while (1) {
        printf("[LCD] Display - Temperature: %.2f°C | Pressure: %.2f bar | Heater: %s | Valve: %s\n",
               temperature, pressure, heater_status ? "ON" : "OFF", 
               valve_position ? "OPEN" : "CLOSED");
        sleep(2);
    }
    return NULL;
}

// TCP Server for Remote Control
void *tcp_server(void *arg) {
    int server_fd, new_socket;
    struct sockaddr_in server_addr, client_addr;
    char buffer[1024] = {0};
    socklen_t addr_len = sizeof(client_addr);

    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(8080);

    if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("Binding failed");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 3) < 0) {
        perror("Listening failed");
        exit(EXIT_FAILURE);
    }

    printf("[TCP] Remote monitoring available on port 8080...\n");

    if ((new_socket = accept(server_fd, (struct sockaddr*)&client_addr, &addr_len)) < 0) {
        perror("Connection failed");
        exit(EXIT_FAILURE);
    }

    printf("[TCP] Remote operator connected.\n");

    while (1) {
        memset(buffer, 0, sizeof(buffer));
        read(new_socket, buffer, sizeof(buffer));

        if (strncmp(buffer, "READ_TEMP", 9) == 0) {
            snprintf(buffer, sizeof(buffer), "Temperature: %.2f°C\n", temperature);
            send(new_socket, buffer, strlen(buffer), 0);
        } 
        else if (strncmp(buffer, "READ_PRESS", 10) == 0) {
            snprintf(buffer, sizeof(buffer), "Pressure: %.2f bar\n", pressure);
            send(new_socket, buffer, strlen(buffer), 0);
        } 
        else if (strncmp(buffer, "HEATER_ON", 9) == 0) {
            set_heater(true);
            send(new_socket, "Heater turned ON\n", 17, 0);
        } 
        else if (strncmp(buffer, "HEATER_OFF", 10) == 0) {
            set_heater(false);
            send(new_socket, "Heater turned OFF\n", 18, 0);
        } 
        else if (strncmp(buffer, "SET_VALVE", 9) == 0) {
            float pos = atof(buffer + 10);
            set_valve_position(pos);
            send(new_socket, "Valve position updated\n", 23, 0);
        } 
        else if (strncmp(buffer, "EXIT", 4) == 0) {
            printf("[TCP] Closing connection.\n");
            break;
        } 
        else {
            send(new_socket, "Unknown command\n", 16, 0);
        }
    }

    close(new_socket);
    close(server_fd);
    return NULL;
}

int main() {
    pthread_t t_thread, p_thread, s_thread, tcp_thread;

    pthread_create(&t_thread, NULL, temperature_process, NULL);
    pthread_create(&p_thread, NULL, pressure_process, NULL);
    pthread_create(&s_thread, NULL, display_process, NULL);
    pthread_create(&tcp_thread, NULL, tcp_server, NULL);

    
    pthread_join(t_thread, NULL);
    pthread_join(p_thread, NULL);
    pthread_join(s_thread, NULL);
    pthread_join(tcp_thread, NULL);

    return 0;
}

