(define (domain swords-and-dragons)
     :requirements :strips
     :types agent location hidden-item
     :predicates
       (at ?x ?loc)
       (has ?x ?item)
       (hidden ?item ?loc)
       (asleep dragon ?loc)
     :action take-sword
       :parameters (?agent ?cave)
       :precondition (and (at ?agent ?cave) (hidden sword ?cave))
       :effect (and (not (hidden sword ?cave)) (has ?agent sword))
     :action wake-dragon
       :parameters (?agent ?dragon-location)
       :precondition (and (at ?agent ?dragon-location) (asleep dragon ?dragon-location))
       :effect (not (asleep dragon ?dragon-location))
     :action fight-dragon
       :parameters (?hero ?dragon)
       :precondition (and (has ?hero sword) (at ?hero ?dragon-location) (asleep dragon ?dragon-location))
       :effect (and (not (asleep dragon ?dragon-location)) (not (at ?hero ?dragon-location)))
   )