(define (domain quest)
  (:types
    agent - Hero
    location - Location
    object - Object
    monster - Monster
  )

  (:predicates
    (at ?a - agent ?l - location) ; at location
    (on-ground ?o - object ?l - location) ; on ground at location
    (sleeping ?m - Monster) ; sleeping monster
    (carrying ?a - Hero ?o - Object) ; carrying object
    (defeated ?m - Monster) ; defeated monster
  )

  (:action
    move-from-to (?a - Hero ?l1 - Location ?l2 - Location)
      :parameters (?a - Hero ?l1 - Location ?l2 - Location)
      :preconditions ((at ?a ?l1))
      :effects ((at ?a ?l2))
    pick-up (?a - Hero ?o - Object ?l - Location)
      :parameters (?a - Hero ?o - Object ?l - Location)
      :preconditions ((on-ground ?o ?l) (not (carrying ?a ?o)))
      :effects ((carrying ?a ?o))
    use-sword (?a - Hero ?m - Monster ?l - Location)
      :parameters (?a - Hero ?m - Monster ?l - Location)
      :preconditions ((at ?a ?l) (carrying ?a sword_of_fire))
      :effects ((defeated ?m))
  )

  ; Add a comment explaining the goal actions in case new actions are added in the future.
  (:goal
    (and
      (at hero tower_of_varnak)
      (carrying hero sword_of_fire)
      (defeated ice_dragon)
    )
  )
)