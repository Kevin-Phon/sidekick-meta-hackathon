"""Fictional, stable-ID event demo fixtures. No private account data."""

def agent_demo(stage):
    updated = stage == 'update'
    return [
        dict(connection_id='agent-demo', provider_id='lecture', kind='lecture', title='Sets · fictional lecture',
             body='A set contains distinct elements. Intersection contains elements in both sets. Union contains elements in either set. Check |A union B| = |A| + |B| - |A intersection B|.',
             metadata={'demo':True,'course':'Sample Discrete Structures'}),
        dict(connection_id='agent-demo', provider_id='assignment', kind='assignment', title='Set operations · fictional practice',
             body='Practice, not a graded assessment. Given A={1,2,3} and B={3,4}, explain union and intersection and check their sizes. ' + ('Deadline moved earlier: November 4 at noon Pacific.' if updated else 'Prepare by November 5 at noon Pacific.'),
             due_at='2026-11-04T12:00:00-08:00' if updated else '2026-11-05T12:00:00-08:00',
             metadata={'demo':True,'course':'Sample Discrete Structures'}),
        dict(connection_id='agent-demo', provider_id='project', kind='project_note', title='Harbor · fictional project check-in',
             body='Project: Harbor, an example campus dashboard. Completed: source import screen. Blocked: missing-file error handling has not been tested. Next: test missing-file handling. ' + ('New meeting requirement: show the error state and bring a 60-second progress update.' if updated else 'Bring a brief progress update to the check-in.'),
             due_at='2026-11-04T15:00:00-08:00', metadata={'demo':True,'project':'Harbor'}),
        dict(connection_id='agent-demo', provider_id='mail', kind='mail', title='Harbor update · fictional saved email',
             body='Saved example message; no real inbox was checked. Harbor check-in is November 4 at 3 PM Pacific. ' + ('Please demonstrate the missing-file error state and explain the blocker.' if updated else 'Please share progress, blockers and next steps.'),
             metadata={'demo':True})]
