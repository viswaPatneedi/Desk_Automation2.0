Method Name : Netflix App Launch and PLAYBACK

User Input Fields (UI Configuration)
> APP LOGIN URL: URL used for activation (Default: http://netflix.com/tv2)
> APP CREDENTIALS:
    Username: User-provided string
    Password: User-provided string.
    
> ASSET VOICE COMMAND: Voice command phrase used to launch specific content
> PLAYBACK LOG STRING: Log line pattern to validate active video playback (Default: Playerstate.playing)
> EXECUTE PLAYBACK CONTROLS: Optional checkbox/toggle to enable or skip trickplay actions (Fast-Forward, Rewind, Play,   Pause).
> PLAYBACK DURATION: This should consider when the playback has started, it need to play the asset till the time provided in here

Automation Workflow Execution Steps

Step 1: App Launch
 > Send a voice command to launch the app "NETFLIX"
 > Wait for 20 seconds.

Step 2: Launch Verification

> Run the terminal command: appsservicectl dumpsys RunTimeManager | grep -i Visible | awk '{print $1}'
    COMMAND: appsservicectl dumpsys RunTimeManager | grep -i Visible | awk '{print $1}'
    output:
    root@apache-4k:~# appsservicectl dumpsys RunTimeManager | grep -i Visible | awk '{print $1}'
    NetflixApp
> Verify that the command output contains the APP NAME. [NetflixApp]
> Inspect /opt/logs/sky-messages.log to confirm it contains the exact string: 'App has screen:  "NetflixApp"'.
    commands: grep -i 'App.*has.*screen' /opt/logs/sky-messages.log | tail -1;grep -i 'Netflix.*Status.*RUNNING' /opt/logs/sky-messages.log | tail -1

    output: 
    root@apache-4k:~# grep -i 'App.*has.*screen' /opt/logs/sky-messages.log | tail -1;grep -i 'Netflix.*Status.*Running' /opt/logs/sky-messages.log | tail -1
    2026-07-22T20:11:38.878Z com.sky.as.apps_com.bskyb.epgui[1750]:  AppsModel.log: [Persistent App] App has screen:  "NetflixApp"
    2026-07-22T20:10:31.854Z com.sky.as.apps_com.bskyb.epgui[1750]:  AppsModel.log: "AS Status update: appId: NetflixApp status:RUNNING"

Step 3: Screen State Identification
    > Capture a screenshot of the current display.
    > Compare the screenshot against reference images to identify the active state.
    > Log the detected screen state to the terminal interface. Valid states include:
        > NETFLIX LOGIN SCREEN
        > NETFLIX PROFILE SCREEN
        > NETFLIX HOME SCREEN

Step 4: Screen State Conditional Handling

    > IF LOGIN SCREEN is detected:
        > OCR/capture the activation code displayed on the television screen.
        > Print the captured code to the terminal log.
        > Open a headless browser or API request to the LOGIN URL.
        > Input the captured activation code, Username, and Password to complete authentication.[but after entered username it will show the OTP to enter, to enter the password one more link called as "Get More help" by clicking on it, then it will show 'Use Password Instead', need to choose that and then enter the account password]
    
    > IF PROFILE SCREEN is detected:
        > Send an ENTER keypress to select the Profile.
        > Wait 5 seconds.
        > Take a verification screenshot to confirm navigation landed on the NETFLIX ASSET SCREEN

    > IF HOME SCREEN is detected:
        > Proceed directly to Step 5.

Step 5: Content Launch
        > Send the ASSET VOICE COMMAND to load the specific video asset.
        > Wait 5 seconds.
        > Take a screenshot to validate that the requested asset page has loaded

Step 6: Playback Initiation
        > Send an ENTER keypress to play the asset.
        > Wait 15 seconds
    
Step 7: Continuous Playback Monitoring
        > Check /opt/logs/sky-messages.log for the PLAYBACK LOG STRING (.*get_state.*returned.*1.*state.*PLAYING.*).
            should consider the Playback log, after the ASSET VOICE COMMAND only
            command: grep -i "state.*PLAYING.*" /opt/logs/sky-messages.log | tail -1
            OUTPUT:
            2026-07-22T20:26:28.681Z com.sky.as.apps_NetflixApp[1750]:  00:20:37.472 [NBP_POOL [1]:0xebe63140] MEDIAPLAYBACK(warn): Telling gstreamer to start playing
            2026-07-22T20:26:28.706Z com.sky.as.apps_NetflixApp[1750]:  00:20:37.500 [REFERENCE_DPI_VIDEO_DECODER:0xe797f140] MEDIACONTROL(warn): PlaybackGroupNative::gstBusCallback() old_state PAUSED, new_state PLAYING, pending VOID_PENDING
           
        > Every 15 seconds during playback, concurrently check the following:
            Run the foreground app check command: "appsservicectl dumpsys RunTimeManager | grep -i Visible | awk '{print $1}'"
        
        > Failure Condition: 
            If the terminal command does not return "NETFLIX" when the foreground app check command is continuously checking, then fail the test step and log: "Netflix app is not running".
        
        > 

Step 8: Trickplay Controls (Optional User Selection)
    > If the EXECUTE PLAYBACK CONTROLS option is enabled in the UI, execute and verify the following sequences:
        Fast-Forward (FF) Sequence:
            > Send 3 to 4 sequential RIGHT keypresses with a strict 0.5-second gap between each press.
            > Parse /opt/logs/sky-messages.log filtering by the exact execution timestamp.
            > Confirm corresponding fast-forward trigger logs are present.
            
        
        Rewind (REW) Sequence:
            > Send 3 to 4 sequential LEFT keypresses with a strict 0.5-second gap between each press.
            > Parse /opt/logs/sky-messages.log filtering by the exact execution timestamp.
            > Confirm corresponding fast-forward trigger logs are present.
        
        Pause & Play Sequence:
            > Send a ENTER keypress for PAUSE
            > Verify /opt/logs/sky-messages.
            > log registers the state transition (PlayerState.pause).
                Command:
                Validate for PAUSE: grep -i "state.*PAUSED" /opt/logs/sky-messages.log | tail -1
                2026-07-22T20:38:09.087Z com.sky.as.apps_NetflixApp[1750]:  00:32:17.879 [NBP_POOL [2]:0xebe18140] MEDIACONTROL(warn): getPipelineState: state change succeeded, get_state returned: 1, state: PAUSED pending: VOID_PENDING
            > Send a ENTER keypress for PLAY
            > Verify log returns to the playing state (PlayerState.PLAYING)
                command:
                Validate for PLAYING: grep -i "state.*PLAYING.*" /opt/logs/sky-messages.log | tail -1
                2026-07-22T20:26:28.707Z com.sky.as.apps_NetflixApp[1750]:  00:20:37.500 [REFERENCE_DPI_VIDEO_DECODER:0xebe7c140] MEDIACONTROL(warn): getPipelineState: state change succeeded, get_state returned: 1, state: PLAYING pending: VOID_PENDING

Step 9: System Crash Analysis
    > Check for application or system failures by executing: grep -i '.process crash.*' /opt/logs/core_logs.txt