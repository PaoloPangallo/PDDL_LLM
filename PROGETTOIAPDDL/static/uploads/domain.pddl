(define (domain quest)
  (:types
    ; define types here
    agent - ?
    location - ?
    object - ?
    monster - ?

  (:predicates
    ; define predicates here
    (at ?a - agent ?l - location) ; at location
    (on-ground ?o - object ?l - location) ; on ground at location
    (sleeping ?m - monster) ; sleeping monster
    (carrying ?a - agent ?o - object) ; carrying object
    (defeated ?m - monster) ; defeated monster

  (:action
    ; define actions here
    move-from-to (?a - agent ?l1 - location ?l2 - location)
      :parameters (?a - agent ?l1 - location ?l2 - location)
      :preconditions ((at ?a ?l1)) 
      :effects ((at ?a ?l2))
    
    pick-up (?a - agent ?o - object ?l - location)
      :parameters (?a - agent ?o - object ?l - location)
      :preconditions ((on-ground ?o ?l) (not (carrying ?a ?o))) 
      :effects ((carrying ?a ?o))
    
    use-sword (?a - agent ?m - monster ?l - location)
      :parameters (?a - agent ?m - monster ?l - location)
      :preconditions ((at ?a ?l) (carrying ?a ?o - object)) 
      :effects ((defeated ?m))

  (:goal
    ; define goal conditions here
    (and
      (at hero tower_of_varnak)
      (carrying hero sword_of_fire)
      (defeated ice_dragon)