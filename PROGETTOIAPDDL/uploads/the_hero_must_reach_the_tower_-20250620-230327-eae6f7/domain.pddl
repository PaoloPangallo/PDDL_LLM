(define (domain blocks-world)
  (:requirements :strips :equality :typing :quantifiers)
  (:types block object agent)
  (:predicates
    (on ?a - block ?b - object)
    (clear ?x - block)
    (holding ?a - agent)
    (blockp ?x - block)
    (objectp ?x - object))
  (:action pick-up
    :parameters (?a - block) (?g - agent))
    (:effect (and (not (clear ?a)) (holding ?a ?g))))

  (:action put-down
    :parameters (?a - block) (?g - agent))
    (:effect (and (clear ?a) (not (holding ?a ?g))))

  (:action stack
    :parameters (?b1 - block) (?b2 - block) (?g - agent))
    (:condition (and (blockp ?b1) (blockp ?b2)))
    (:effect (and (not (clear ?b1)) (on ?b1 ?b2) (clear ?b2))))

  (:action unstack
    :parameters (?b1 - block) (?b2 - block) (?g - agent))
    (:condition (and (blockp ?b1) (blockp ?b2) (on ?b1 ?b2)))
    (:effect (and (clear ?b1) (not (on ?b1 ?b2))))
  :action stacking-sequence
    :parameters (?bs - sequence-of blocks) (?g - agent))
    (:condition (every (blockp ?x) ?bs))
    (:effect (if (len ?bs) (and (not (clear (first ?bs))) (stack (first ?bs) (rest ?bs) ?g)))))
  :action unstacking-sequence
    :parameters (?bs - sequence-of blocks) (?g - agent))
    (:condition (every (blockp ?x) ?bs))
    (:effect (if (len ?bs) (and (clear (first ?bs)) (unstack (first ?bs) (rest ?bs) ?g))))
  )