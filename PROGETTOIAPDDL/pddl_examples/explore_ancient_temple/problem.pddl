(define (problem temple-exploration)
    (:domain temple)
    (:objects
        indiana - agent
        hall chamber treasure_room - room
        idol - artifact
    )
    (:init
        (at indiana hall)
        (connected hall chamber)
        (connected chamber treasure_room)
        (artifact_in idol treasure_room)
    )
    (:goal
        (and (has indiana idol))
    )
)