(define (domain tower-of-varnak)
    :requirements ((linear))
    :types agent location monster object
    :predicates
      (at ?a ?loc)
      (on-ground ?o ?loc)
      (carrying ?a ?o)
      (sleeping ?m)
      (awake ?m)
      (inventory-item ?a ?o)
    :actions
      (move
        :parameters (?a ?loc1 ?loc2)
        :precondition (and (at ?a ?loc1) (not (on-ground ?a ?loc1)))
        :effect (and (at ?a ?loc2) (not (at ?a ?loc1)) (not (on-ground ?a ?loc1))))
      (pickup
        :parameters (?a ?o ?loc)
        :precondition (and (and (on-ground ?o ?loc) (at ?a ?loc)) (not (carrying ?a ?o)))
        :effect (and (not (on-ground ?o ?loc)) (inventory-item ?a ?o) (carrying ?a ?o))))
  :init
    (and
      (at hero village)
      (on-ground sword-of-fire tower-of-varnak)
      (sleeping ice-dragon)
      (inventory-item hero sword-of-fire))
  :types
    (location village tower-of-varnak)
    (monster sleeping awake)
    (object inventory-item sword sword-of-fire)
  :functions
    (location-north ?loc -1)
    (location-east ?loc 1)
    (location-west ?loc -1)
    (location-south ?loc 1)
    (sleeping-awake ?m 0)
  :action-precedence (:action wake-dragon :action pickup :action move))