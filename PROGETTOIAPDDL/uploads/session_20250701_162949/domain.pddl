(:requirements :strips :equality)
   (:types agent monster location object)
   (:predicates
      (at ?a -agent ?l -location)
      (on-ground ?o -object ?l -location)
      (sleeping ?m -monster)
      (carrying ?h -agent ?o -object)
   )
   (:action move-hero
      (:parameters ?h -agent ?n -location)
      :precondition (and (at ?h ?c) (not (at ?h ?n)))
      :effect (and (not (at ?h ?c)) (at ?h ?n)))
   (:action take-object
      (:parameters ?h -agent ?o -object ?l -location)
      :precondition (and (on-ground ?o ?l) (at ?h ?l))
      :effect (and (not (on-ground ?o ?l)) (carrying ?h ?o)))
   (:action put-object
      (:parameters ?h -agent ?o -object ?n -location)
      :precondition (and (carrying ?h ?o) (at ?h ?n))
      :effect (and (not (carrying ?h ?o)) (on-ground ?o ?n)))
   (:action fight
      (:parameters ?h -agent ?m -monster)
      :precondition (and (at ?h ?l) (sleeping ?m) (carrying sword-of-fire))
      :effect (not sleeping ?m)))