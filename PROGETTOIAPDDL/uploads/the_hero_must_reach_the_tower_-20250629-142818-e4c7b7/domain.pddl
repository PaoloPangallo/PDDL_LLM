(define (domain robot_navigation)
    (:requirements :strips)
    (:types robot location wall obstacle)
    (:predicates
      (at ?r - robot ?l - location)
      (facing ?r - robot north south east west)
      (clear ?l - location)
      (obstacle ?o - obstacle ?l - location)
      (wall ?w - wall ?l - location)
    )

    (:action move
      :parameters (?r - robot ?dir - direction)
      :precondition (and (at ?r ?c) (clear ?c))
      :effect (and (not (at ?r ?c)) (at ?r (if (eql ?dir north) (conjunct (facing ?r north) (next-location ?c (north ?c))))
                    (if (eql ?dir south) (conjunct (facing ?r south) (next-location ?c (south ?c))))
                    (if (eql ?dir east) (conjunct (facing ?r east) (next-location ?c (east ?c))))
                    (if (eql ?dir west) (conjunct (facing ?r west) (next-location ?c (west ?c))))))

    (:action turn
      :parameters (?r - robot ?t - direction)
      :precondition (at ?r ?c)
      :effect (and (not (facing ?r ?c)) (if (eql ?t north) (conjunct (facing ?r north) (next-facing ?c north)))
                    (if (eql ?t south) (conjunct (facing ?r south) (next-facing ?c south)))
                    (if (eql ?t east) (conjunct (facing ?r east) (next-facing ?c east)))
                    (if (eql ?t west) (conjunct (facing ?r west) (next-facing ?c west)))))

    (:action perceive
      :parameters (?r - robot)
      :precondition (at ?r ?c)
      :effect (clear ?c)
      :allow-goal (t))

    (:action remove-obstacle
      :parameters (?r - robot ?o - obstacle ?l - location)
      :precondition (and (at ?r ?l) (obstacle ?o ?l))
      :effect (not (obstacle ?o ?l)))

    (:action place-obstacle
      :parameters (?r - robot ?o - obstacle ?l - location)
      :precondition (and (at ?r ?l) (not (obstacle ?o ?l)))
      :effect (obstacle ?o ?l))

    (:action build-wall
      :parameters (?r - robot ?w - wall ?l - location)
      :precondition (and (at ?r ?l) (not (wall ?w ?l)))
      :effect (wall ?w ?l))
  )