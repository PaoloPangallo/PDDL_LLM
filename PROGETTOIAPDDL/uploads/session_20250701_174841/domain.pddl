(:requirements :equality :action-precondition :fluent :typing)
  (:types agent location monster object)
  (:predicates
    (at ?a ?l)                       ; Agent is at Location
    (on-ground ?o ?l)                ; Object is on the Ground at Location
    (carrying ?a ?o)                 ; Agent carries an Object
    (sleeping ?m))                   ; Monster is asleep

  (:action take-sword
    :parameters (?a - agent)
              (?l - location)
              (?o - object)
    :precondition (and (at ?a ?l) (on-ground ?o ?l))
    :effect (and (not (on-ground ?o ?l)) (carrying ?a ?o))))

  (:action drop-sword
    :parameters (?a - agent)
              (?l - location)
    :precondition (carrying ?a ?o))
    :effect (and (at ?o ?l) (not (carrying ?a ?o))))

  (:action move-to
    :parameters (?a - agent)
              (?l1 - location)
              (?l2 - location)
    :precondition (at ?a ?l1))
    :effect (at ?a ?l2)))

  (:action wake-dragon
    :parameters (?a - agent)
              (?m - monster))
    :precondition (and (at ?a tower-of-varnak) (carrying sword-of-fire)))
    :effect (not (sleeping ?m)))

  (:action fight
    :parameters (?a - agent)
              (?m - monster))
    :precondition (and (at ?a tower-of-varnak) (awake ?m)))
    :effect (not (exists ?m (sleeping ?m))))