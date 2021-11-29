# <img src='https://0000.us/klatchat/app/files/neon_images/icons/neon_skill.png' card_color="#FF8600" width="50" style="vertical-align:bottom">User Settings

## Summary

Have Neon help you change and control your user settings.

## Requirements

No special required packages for this skill.

## Description

Neon can help you control your user preference settings via this skill.

## Examples

You can use this skill in multiple ways: 
* change my units to (metric/imperial)
* enable listening confirmation
* (enable/disable) clap commands 
* talk to me (faster/slower/normally) 
* change my wakeword to "okay computer"
* (enable/disable) (audio recording/transcriptions) 
* change my location to (Seattle)
* change clap commands to my (home/audio/default) set
* show neon brain
  
  

## Location

    ${skills}/user-settings-control.neon

## Files
    
    ${skills}/user-settings-control.neon/__init__.py
    ${skills}/user-settings-control.neon/test
    ${skills}/user-settings-control.neon/test/intent
    ${skills}/user-settings-control.neon/test/intent/StartClapper.intent.json
    ${skills}/user-settings-control.neon/test/intent/DenyTranscription.intent.json
    ${skills}/user-settings-control.neon/test/intent/ConfirmIntentNo.intent.json
    ${skills}/user-settings-control.neon/test/intent/PermitTranscription.intent.json
    ${skills}/user-settings-control.neon/test/intent/ConfirmIntentYes.intent.json
    ${skills}/user-settings-control.neon/test/intent/ChangeMeasuring.json
    ${skills}/user-settings-control.neon/settings.json
    ${skills}/user-settings-control.neon/vocab
    ${skills}/user-settings-control.neon/vocab/en-us
    ${skills}/user-settings-control.neon/vocab/en-us/StartClapper.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Speed.voc
    ${skills}/user-settings-control.neon/vocab/en-us/With.voc
    ${skills}/user-settings-control.neon/vocab/en-us/ConfirmListening.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Units.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Military.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Brain.voc
    ${skills}/user-settings-control.neon/vocab/en-us/My.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Permit1.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Show.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Time.voc
    ${skills}/user-settings-control.neon/vocab/en-us/ClapperMenu.voc
    ${skills}/user-settings-control.neon/vocab/en-us/American.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Change.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Settings.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Transcription2.voc
    ${skills}/user-settings-control.neon/vocab/en-us/ConfirmNo.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Talk.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Setup.voc
    ${skills}/user-settings-control.neon/vocab/en-us/ConfirmYes.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Clap.voc
    ${skills}/user-settings-control.neon/vocab/en-us/AudioHome.voc
    ${skills}/user-settings-control.neon/vocab/en-us/To.voc
    ${skills}/user-settings-control.neon/vocab/en-us/SetChange.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Deny1.voc
    ${skills}/user-settings-control.neon/vocab/en-us/WW.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Scene.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Transcription3.voc
    ${skills}/user-settings-control.neon/vocab/en-us/Location.voc
    ${skills}/user-settings-control.neon/vocab/en-us/OnStartup.voc
    ${skills}/user-settings-control.neon/vocab/en-us/CallYou.voc
    ${skills}/user-settings-control.neon/README.md


  

## Class Diagram

[Click here](https://0000.us/klatchat/app/files/neon_images/class_diagrams/user-settings-control.png)

## Available Intents
<details>
<summary>Click to expand.</summary>
<br>

### StartClapper.voc
    clapper
    clap
    clapp
    claps
    
### Speed.voc
    faster
    slower
    normally
    
### With.voc
    with
    while
    
### ConfirmListening.voc
    confirm listening
    listening confirmation
    ding
    
### Units.voc
    units
    measuring system
    
### Military.voc
    military
    24
    european
    full
    metric
    
### Brain.voc
    neon brain
    brain
    system brain
    debug window
    
### My.voc
    my
    my system
    
### Permit1.voc
    permit
    allow
    start
    begin
    enable
    
### Show.voc
    showing
    displaying
    display
    
### Time.voc
    time
    
### ClapperMenu.voc
    tell me my clap commands
    tell me my clapper menu
    tell me my clapper process menu
    
### American.voc
    imperial
    american
    12
    
### Change.voc
    change
    switch
    update
    set
    
### Settings.voc
    setting
    settings
    gestures
    gesture
    action
    commands
    command
    function
    
### Transcription2.voc
    transcription
    text
    
### ConfirmNo.voc
    no never mind
    
### Talk.voc
    talk to me
    
### Setup.voc
    setup
    set up
    configuration
    first run
    calibrate
    
### ConfirmYes.voc
    yes
    continue
    go ahead
    begin
    start
    
### Clap.voc
    clappper
    clapper process
    clap commands
    club commands
    
### AudioHome.voc
    audio
    home control
    home
    default
    
### To.voc
    to
    
### SetChange.voc
    set
    change
    
### Deny1.voc
    deny
    quit
    end
    disable
    
### WW.voc
    wake word
    ww
    wake words
    wakeword
    
### Scene.voc
    scene
    settings
    set
    preset
    
### Transcription3.voc
    audio
    text
    
### Location.voc
    location
    
### OnStartup.voc
    on startup
    by default
    
### CallYou.voc
    i will call you
    your new name is

</details>  

## Details

### Text
        Enable clap commands.
        >> Clapper is active
        
        Disable clap commands.
        >> Clapper is inactive


        Talk to me faster.
        >> I will talk faster.
        
        Talk to me normally.
        >> I will talk normally.
 
 
### Picture

### Video

  

## Contact Support

Use the [link](https://neongecko.com/ContactUs) or [submit an issue on GitHub](https://help.github.com/en/articles/creating-an-issue)

## Credits
[reginaneon](https://github.com/reginaneon)
[NeonGeckoCom](https://github.com/NeonGeckoCom)

## Tags
#NeonGecko Original
#NeonAI
