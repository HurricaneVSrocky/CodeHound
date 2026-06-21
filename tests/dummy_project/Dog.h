#pragma once
#include "Animal.h"

namespace Zoo {

    class Dog : public Animal {
    private:
        std::string breed;

    public:
        Dog(const std::string& n, int a, const std::string& b);
        
        void makeSound() const override;
        void fetch() const;
        void dangerousAction() const; // AI testing target
    };

}
