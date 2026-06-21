#include "Dog.h"
#include <iostream>

namespace Zoo {

    int GlobalAnimalCount = 0;
    int* DangerPointer = nullptr; // Uninitialized pointer for AI to track

    void Animal::move() const {
        std::cout << name << " is moving..." << std::endl;
    }

    Dog::Dog(const std::string& n, int a, const std::string& b) 
        : Animal(n, a), breed(b) {
        GlobalAnimalCount++; // Writes GlobalAnimalCount
    }

    void Dog::makeSound() const {
        std::cout << name << " says Woof! " << GlobalAnimalCount << " animals exist." << std::endl; // Reads GlobalAnimalCount
    }

    void Dog::fetch() const {
        move(); // Calls Animal::move
        std::cout << name << " is fetching the ball!" << std::endl;
    }

    void Dog::dangerousAction() const {
        std::cout << name << " is doing something dangerous..." << std::endl;
        *DangerPointer = 42; // Crash! Writes to nullptr
    }

}
