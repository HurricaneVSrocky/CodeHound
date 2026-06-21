#include "Dog.h"
#include "Animal.h"
#include <iostream>

using namespace Zoo;

void interactWithDog(const Dog& d) {
    d.makeSound(); // Calls Dog::makeSound
    d.fetch();     // Calls Dog::fetch
}

int main() {
    Dog myDog("Buddy", 3, "Golden Retriever"); // Calls Dog constructor
    
    interactWithDog(myDog); // Calls interactWithDog
    myDog.dangerousAction(); // Trigger the AI crash test
    
    std::cout << "Total animals: " << GlobalAnimalCount << std::endl; // Reads GlobalAnimalCount
    return 0;
}
