(define (problem explore-cave)
    (:domain world-exploration)
    (:objects cave treasure1 treasure2)
    (:init
      (at cave)
      (on treasure1 cave)
      (on treasure2 cave))
    (:goal (and (at cave) (not (on treasure1 cave)) (not (on treasure2 cave))))
  )