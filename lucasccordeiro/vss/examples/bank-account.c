#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <assert.h>

pthread_mutex_t account_mutex = PTHREAD_MUTEX_INITIALIZER;

int balance = 1000;  // Shared bank account balance

void* withdraw(void* arg) {
    int amount = *(int*)arg;

    pthread_mutex_lock(&account_mutex);    
    // Check if we have enough money
    if (balance >= amount) {
        printf("Thread %ld: Checking balance... $%d available\n", 
               pthread_self(), balance);
        
        // Simulate some processing time (ATM communication, etc.)
        usleep(100000);  // 100ms delay
        
        // Withdraw the money
        balance -= amount;
        printf("Thread %ld: Withdrew $%d, new balance: $%d\n", 
               pthread_self(), amount, balance);
    } else {
        printf("Thread %ld: Insufficient funds for $%d withdrawal\n", 
               pthread_self(), amount);
    }
    pthread_mutex_unlock(&account_mutex);
    return NULL;
}

int main() {
    pthread_t thread1, thread2;
    int amount1 = 800;
    int amount2 = 600;
    
    printf("Initial balance: $%d\n", balance);
    
    // Two people trying to withdraw money simultaneously
    pthread_create(&thread1, NULL, withdraw, &amount1);
    pthread_create(&thread2, NULL, withdraw, &amount2);
    
    pthread_join(thread1, NULL);
    pthread_join(thread2, NULL);
    
    // The account must never be overdrawn.
    assert(balance >= 0);

    printf("Final balance: $%d\n", balance);
    
    return 0;
}

