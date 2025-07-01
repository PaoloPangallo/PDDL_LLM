(:domain quest)
   (:requirements :strips :equivalent-objects)
   (:types agent location object monster)
   (:predicates
      (at ?a -agent -location)
      (on-ground ?o -object)
      (carrying ?h -hero -object)
      (awake ?m -monster)
      (defeated ?m -monster)
   )
   (:action move
      (:parameters ?a -agent ?l -location)
      (:effect (at ?a ?l)))
   (:action pickup
      (:parameters ?h -hero ?o -object)
      (:condition (on-ground ?o))
      (:effect (not (on-ground ?o)) (carrying ?h ?o)))
   (:action drop
      (:parameters ?h -hero ?o -object)
      (:condition (and (carrying ?h ?o) (at ?h ?l)))
      (:effect (on-ground ?o) (not (carrying ?h ?o))))
   (:action fight
      (:parameters ?h -hero ?m -monster)
      (:condition (and (carrying ?h sword-of-fire) (awake ?m)))
      (:effect (defeated ?m)))