#pragma once

#include <string>

namespace Zoo {

    extern int GlobalAnimalCount; // Will be modified by implementations

    class Animal {
    protected:
        std::string name;
        int age;

    public:
        Animal(const std::string& n, int a) : name(n), age(a) {}
        virtual ~Animal() = default;

        virtual void makeSound() const = 0;
        virtual void move() const;
        
        std::string getName() const { return name; }
    };

}
