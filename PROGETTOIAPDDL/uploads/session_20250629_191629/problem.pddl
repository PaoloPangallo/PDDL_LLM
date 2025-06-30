(define (problem toy_collection)
    (:domain simple_world)
    (:objects
      agent1 - agent
      home store - location
      toy1 toy2 - object)
    (:init
      (and (at agent1 home)
           (not (has-object agent1 toy1))
           (not (has-object agent1 toy2)))
      (and (at-object toy1 store)
           (at-object toy2 store))
    )
    (:goal (and (has-object agent1 toy1) (has-object agent1 toy2))))