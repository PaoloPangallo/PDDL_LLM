(define (problem robot-construction)
    (:domain robot-assembly)
    (:objects
      robot1 robot2 - robot
      assembly-line1 - assembly-line
      part1 part2 part3 - part
    )
    (:init
      (at-robot robot1 assembly-line1)
      (has-part robot1 unassembled)
      (has-part robot2 unassembled)
      (not (assembled assembly-line1))
    )
    (:goal (and (assembled assembly-line1)))
  )